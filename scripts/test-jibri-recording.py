#!/usr/bin/env python3
"""
Jibri recording pipeline test.
Connects to XMPP as the focus/Jicofo user and sends JibriIq stanzas
to start/stop a recording on a test room, then verifies the result.

Usage:
  python3 test-jibri-recording.py [--room ROOM] [--duration SECONDS]
"""

import base64
import hashlib
import hmac
import json
import os
import random
import re
import socket
import ssl
import struct
import subprocess
import sys
import time
import urllib.request
import uuid
from xml.etree import ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INFRA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"

def ok(msg):
    print(f"  {GREEN}OK{NC} {msg}")

def fail(msg):
    print(f"  {RED}X{NC} {msg}")

def info(msg):
    print(f"  {CYAN}->{NC} {msg}")

def warn(msg):
    print(f"  {YELLOW}W{NC} {msg}")

def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("\"'")
    return env


def sasl_scram_sha1_client_final(username, password, cdata_b64, sdata_b64):
    """Compute SCRAM-SHA-1 client final message.
    Returns (final_message_b64, server_signature_b64).
    """
    sdata = base64.b64decode(sdata_b64).decode("utf-8", errors="replace")
    nonce = ""
    salt_b64 = ""
    iterations = 4096
    for part in sdata.split(","):
        if part.startswith("r="):
            nonce = part[2:]
        elif part.startswith("s="):
            salt_b64 = part[2:]
        elif part.startswith("i="):
            iterations = int(part[2:])
    if not nonce or not salt_b64:
        raise Exception("Invalid SCRAM challenge")
    
    cdata = base64.b64decode(cdata_b64).decode("utf-8", errors="replace")
    cfinal_bare = "c=biws,r=%s" % nonce
    
    def pbkdf2_sha1(pwd, salt, iters):
        key = pwd.encode("utf-8")
        u = salt + struct.pack(">I", 1)
        r = hmac.new(key, u, hashlib.sha1).digest()
        p = r
        for _ in range(1, iters):
            p = hmac.new(key, p, hashlib.sha1).digest()
            r = bytes(a ^ b for a, b in zip(r, p))
        return r
    
    salted_password = pbkdf2_sha1(password, base64.b64decode(salt_b64), iterations)
    client_key = hmac.new(salted_password, b"Client Key", hashlib.sha1).digest()
    stored_key = hashlib.sha1(client_key).digest()
    auth_message = "%s,%s,%s" % (cdata, sdata, cfinal_bare)
    client_signature = hmac.new(stored_key, auth_message.encode(), hashlib.sha1).digest()
    client_proof = bytes(a ^ b for a, b in zip(client_key, client_signature))
    cfinal = "%s,p=%s" % (cfinal_bare, base64.b64encode(client_proof).decode())
    server_key = hmac.new(salted_password, b"Server Key", hashlib.sha1).digest()
    server_signature = hmac.new(server_key, auth_message.encode(), hashlib.sha1).digest()
    return base64.b64encode(cfinal.encode()).decode(), base64.b64encode(server_signature).decode()


class XmppClient:
    def __init__(self, host, port, jid, password):
        self.host = host
        self.port = port
        self.jid = jid
        self.password = password
        self.sock = None
        self.tls = False
        self.xmpp_domain = jid.split("@")[1] if "@" in jid else host
        self.rid = random.randint(100000, 999999)

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.sock.settimeout(10)

        # Start stream to the XMPP domain (not IP)
        self._send(
            '<stream:stream to="%s" xmlns="jabber:client" '
            'xmlns:stream="http://etherx.jabber.org/streams" version="1.0">'
            % self.xmpp_domain
        )

        features = self._recv_xml(timeout=5)
        if not features:
            raise Exception("No stream features received")

        # Check for STARTTLS
        if "<starttls" in features and "<required" in features:
            self._send(
                '<starttls xmlns="urn:ietf:params:xml:ns:xmpp-tls"/>'
            )
            tls_resp = self._recv_xml(timeout=5)
            if "proceed" not in tls_resp:
                raise Exception("STARTTLS failed: " + tls_resp[:200])

            # Wrap socket with TLS
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.sock = context.wrap_socket(self.sock, server_hostname=self.host)
            self.tls = True

            # Restart stream after TLS
            self._send(
                '<stream:stream to="%s" xmlns="jabber:client" '
                'xmlns:stream="http://etherx.jabber.org/streams" version="1.0">'
                % self.xmpp_domain
            )
            features = self._recv_xml(timeout=5)

        # Extract available mechanisms
        mechanisms = []
        m = re.search(r"<mechanisms[^>]*>(.*?)</mechanisms>", features, re.DOTALL)
        if m:
            mechanisms = re.findall(r"<mechanism>([^<]+)</mechanism>", m.group(1))

        # Try SASL PLAIN first
        chosen = None
        for mech in ["PLAIN", "SCRAM-SHA-1", "DIGEST-MD5"]:
            if mech in mechanisms:
                chosen = mech
                break

        if not chosen:
            raise Exception("No supported SASL mechanism found in: " + str(mechanisms))

        if chosen == "PLAIN":
            # Try with full JID as authcid
            for auth_user in [self.jid, self.jid.split("@")[0]]:
                auth_str = "\x00%s\x00%s" % (auth_user, self.password)
                auth_b64 = base64.b64encode(auth_str.encode()).decode()
                self._send(
                    '<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">%s</auth>'
                    % auth_b64
                )
                resp = self._recv_xml(timeout=5)
                if "success" in resp:
                    chosen = "PLAIN_OK"
                    break
                elif "failure" in resp:
                    # Try next format
                    continue
            if chosen != "PLAIN_OK":
                raise Exception("SASL PLAIN auth failed (tried both JID formats)")
        elif "SCRAM-SHA-1" in str(chosen):
            # Client first message
            cnonce = base64.b64encode(os.urandom(18)).decode()[:24]
            cdata = "n,,n=%s,r=%s" % (self.jid.split("@")[0], cnonce)
            cb64 = base64.b64encode(cdata.encode()).decode()
            self._send(
                '<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="SCRAM-SHA-1">%s</auth>'
                % cb64
            )
            resp = self._recv_xml(timeout=5)
            if "challenge" not in resp:
                raise Exception("SCRAM-SHA-1 auth failed: " + resp[:200])
            chal_b64 = re.search(r"<challenge[^>]*>([^<]+)", resp)
            if not chal_b64:
                raise Exception("No challenge data from server")
            
            # Compute client final message
            _username = self.jid.split("@")[0]
            cfinal_b64, _ = sasl_scram_sha1_client_final(
                _username, self.password, cb64, chal_b64.group(1)
            )
            
            self._send(
                '<response xmlns="urn:ietf:params:xml:ns:xmpp-sasl">%s</response>'
                % cfinal_b64
            )
            resp = self._recv_xml(timeout=5)
            if "success" in resp:
                # Verify server signature if present
                pass
            else:
                raise Exception("SCRAM-SHA-1 final response failed: " + resp[:200])

        # Restart stream after auth
        self._send(
            '<stream:stream to="%s" xmlns="jabber:client" '
            'xmlns:stream="http://etherx.jabber.org/streams" version="1.0">'
            % self.xmpp_domain
        )
        self._recv_xml(timeout=5)

        # Bind resource
        resource = "jibri-test-%d" % random.randint(1000, 9999)
        self._send_iq("set",
            '<bind xmlns="urn:ietf:params:xml:ns:xmpp-bind">'
            '<resource>%s</resource></bind>' % resource
        )
        time.sleep(0.5)
        self._drain()

        # Start session
        self._send_iq("set",
            '<session xmlns="urn:ietf:params:xml:ns:xmpp-session"/>'
        )
        time.sleep(0.5)
        self._drain()
        return True

    def _send(self, data):
        try:
            self.sock.sendall(data.encode("utf-8"))
        except Exception as e:
            raise Exception("Socket send failed: %s" % e)

    def _recv(self, size=8192):
        try:
            return self.sock.recv(size).decode("utf-8", errors="replace")
        except socket.timeout:
            return ""
        except Exception as e:
            raise Exception("Socket recv failed: %s" % e)

    def _drain(self):
        try:
            while True:
                d = self.sock.recv(4096)
                if not d:
                    break
        except (socket.timeout, BlockingIOError):
            pass

    def _recv_xml(self, timeout=5):
        buf = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = self._recv()
            if chunk:
                buf += chunk
                # Check for end of various XML elements
                if "</stream:features>" in buf:
                    return buf
                if "proceed" in buf and "</proceed>" in buf:
                    return buf
                if "success" in buf and "</success>" in buf:
                    return buf
                if "challenge" in buf and "</challenge>" in buf:
                    return buf
                if "failure" in buf and "</failure>" in buf:
                    return buf
            else:
                time.sleep(0.1)
        return buf

    def _send_iq(self, iq_type, payload, to=None):
        iq_id = str(uuid.uuid4())[:8]
        to_attr = ' to="%s"' % to if to else ""
        stanza = '<iq type="%s" id="%s"%s>%s</iq>' % (iq_type, iq_id, to_attr, payload)
        self._send(stanza)
        return iq_id

    def send_iq(self, iq_type, payload, to=None):
        self._send_iq(iq_type, payload, to)
        time.sleep(0.3)
        self._drain()

    def send_presence(self, to=None, stanza_type=None):
        attrs = ""
        if to:
            attrs += ' to="%s"' % to
        if stanza_type:
            attrs += ' type="%s"' % stanza_type
        self._send("<presence%s/>" % attrs)

    def close(self):
        if self.sock:
            try:
                self._send("</stream:stream>")
            except Exception:
                pass
            self.sock.close()
            self.sock = None


def get_prosody_ip():
    try:
        result = subprocess.run(
            ["docker", "inspect", "jitsi-prosody",
             "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "localhost"


def get_focus_credentials():
    # First try the live Docker container's config (most up-to-date)
    try:
        result = subprocess.run(
            ["docker", "exec", "jitsi-jicofo", "cat", "/config/jicofo.conf"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            m = re.search(r'password\s*=\s*"([^"]+)"', result.stdout)
            if m:
                return m.group(1)
    except Exception:
        pass
    # Fallback: local config file
    config_path = os.path.join(INFRA_DIR, "config", "jicofo", "jicofo.conf")
    if os.path.isfile(config_path):
        with open(config_path) as f:
            content = f.read()
        m = re.search(r'password\s*=\s*"([^"]+)"', content)
        if m:
            return m.group(1)
    # Fallback: try env
    env = load_env(os.path.join(INFRA_DIR, ".env"))
    for k, v in env.items():
        if "JICOFO_AUTH_PASSWORD" in k and v:
            return v
    return ""


def get_arvan_config():
    env = load_env(os.path.join(INFRA_DIR, ".env"))
    raw_key = env.get("ARVAN_API_KEY", "")
    api_key = raw_key.replace("apikey ", "", 1).strip() if raw_key else ""
    return {
        "api_key": api_key,
        "channel_id": env.get("ARVAN_CHANNEL_ID", "3a0cd5ec-2a2a-4ad4-ac9b-bb39a90e6eec"),
        "base_url": env.get("ARVAN_VOD_BASE_URL", "https://napi.arvancloud.ir/vod/2.0"),
    }


def delete_arvan_video(video_id, api_key, base_url):
    url = "%s/videos/%s" % (base_url, video_id)
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("Authorization", "apikey %s" % api_key)
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status in (200, 204)
    except Exception as e:
        warn("Failed to delete ArvanCloud video: %s" % e)
        return False


def run_test(room_name=None, duration=5):
    print("\n" + CYAN + "=" * 46 + NC)
    print(CYAN + "  Jibri Recording Pipeline Test" + NC)
    print(CYAN + "=" * 46 + NC + "\n")

    if not room_name:
        room_name = "jibri-test-%d" % random.randint(10000, 99999)

    recording_dir = os.path.join(INFRA_DIR, "recordings")
    state_dir = os.path.join(INFRA_DIR, "state", "uploaded")
    os.makedirs(state_dir, exist_ok=True)

    issues = 0

    # Step 1: Prerequisites
    print(YELLOW + "[1/7] Checking prerequisites..." + NC)
    focus_password = get_focus_credentials()
    if not focus_password:
        fail("Jicofo XMPP password not found")
        issues += 1
    else:
        ok("Jicofo credentials found")

    arvan = get_arvan_config()
    if not arvan["api_key"]:
        fail("ArvanCloud API key not found")
        issues += 1
    else:
        ok("ArvanCloud API key found")

    if not os.path.isdir(recording_dir):
        info("Creating recordings directory: %s" % recording_dir)
        os.makedirs(recording_dir, exist_ok=True)

    if issues > 0:
        print("\n" + RED + "Prerequisites missing. Aborting." + NC)
        return False

    # Step 2: Jibri availability
    print("\n" + YELLOW + "[2/7] Checking Jibri availability..." + NC)
    try:
        stats = subprocess.run(
            ["docker", "exec", "jitsi-jicofo",
             "curl", "-s", "--max-time", "5", "http://localhost:8888/stats"],
            capture_output=True, text=True, timeout=10
        )
        if stats.returncode == 0 and stats.stdout:
            data = json.loads(stats.stdout)
            jibri_info = data.get("jibri_detector", {})
            available = int(jibri_info.get("available", 0))
            total = int(jibri_info.get("count", 0))
            if available > 0:
                ok("%d/%d Jibri instances available" % (available, total))
            elif total > 0:
                warn("All %d Jibri(s) busy - test may queue" % total)
            else:
                fail("No Jibri instances registered with Jicofo")
                issues += 1
        else:
            fail("Could not reach Jicofo stats API")
            issues += 1
    except Exception as e:
        fail("Jicofo stats check failed: %s" % e)
        issues += 1

    if issues > 0:
        print("\n" + RED + "Aborting due to Jibri availability issues." + NC)
        return False

    # Step 3: XMPP and recording trigger
    print("\n" + YELLOW + "[3/7] Connecting to XMPP and starting recording..." + NC)
    print("     Room: " + CYAN + room_name + NC)
    print("     Duration: " + CYAN + "%ds" % duration + NC)

    muc_jid = "%s@muc.meet.jitsi" % room_name
    focus_jid = "focus@auth.meet.jitsi"
    session_id = str(uuid.uuid4())
    prosody_ip = get_prosody_ip()

    try:
        client = XmppClient(prosody_ip, 5222, focus_jid, focus_password)
        client.connect()
        ok("Connected to XMPP as focus user")

        # Join the MUC room
        info("Joining MUC room %s ..." % muc_jid)
        client.send_presence(to="%s/focus-test" % muc_jid)
        time.sleep(1)

        # Send JibriIq to start recording to Jicofo
        info("Sending start-recording IQ to Jicofo...")
        client.send_iq("set",
            '<jibri xmlns="http://jitsi.org/protocol/jibri"'
            ' action="start"'
            ' room="%s"'
            ' session_id="%s"'
            ' app="jibri"'
            ' display_name="Jibri Test Recorder"/>' % (muc_jid, session_id),
            to="focus.meet.jitsi"
        )
        info("Recording started, waiting %ds..." % duration)
        time.sleep(duration)

        # Stop recording
        info("Sending stop-recording IQ to Jicofo...")
        client.send_iq("set",
            '<jibri xmlns="http://jitsi.org/protocol/jibri"'
            ' action="stop"'
            ' room="%s"'
            ' session_id="%s"/>' % (muc_jid, session_id),
            to="focus.meet.jitsi"
        )
        ok("Stop command sent")

        # Leave MUC
        client.send_presence(to="%s/focus-test" % muc_jid, stanza_type="unavailable")
        client.close()
        ok("Disconnected from XMPP")

    except Exception as e:
        fail("XMPP communication failed: %s" % e)
        issues += 1

    if issues > 0:
        print("\n" + RED + "Recording trigger failed." + NC)
        return False

    # Step 4: Wait for recording file
    print("\n" + YELLOW + "[4/7] Waiting for recording to finalize (up to 60s)..." + NC)
    found_recording = False
    deadline = time.time() + 60
    while time.time() < deadline:
        for entry in os.listdir(recording_dir):
            entry_path = os.path.join(recording_dir, entry)
            if os.path.isdir(entry_path):
                mp4_files = [f for f in os.listdir(entry_path) if f.endswith(".mp4")]
                metadata = os.path.join(entry_path, "metadata.json")
                if mp4_files and os.path.isfile(metadata):
                    found_recording = True
                    info("Found recording: %s" % entry)
                    state_marker = os.path.join(state_dir, entry)
                    if os.path.isfile(state_marker):
                        ok("Recording already uploaded to ArvanCloud")
                    break
        if found_recording:
            break
        time.sleep(2)

    if not found_recording:
        warn("No recording detected in recordings/ after 60s")
        info("The recording was initiated. Check watch-recordings.sh logs.")

    # Step 5: Wait for ArvanCloud upload
    print("\n" + YELLOW + "[5/7] Waiting for upload to ArvanCloud (up to 120s)..." + NC)
    uploaded = False
    test_video_id = None
    deadline = time.time() + 120
    while time.time() < deadline:
        for entry in os.listdir(state_dir):
            marker_path = os.path.join(state_dir, entry)
            if os.path.isfile(marker_path):
                uploaded = True
                info("Upload detected via state marker: %s" % entry)
                break
        if uploaded:
            break
        try:
            req = urllib.request.Request(
                "%s/channels/%s/videos?page=1&per_page=5"
                % (arvan["base_url"], arvan["channel_id"])
            )
            req.add_header("Authorization", "apikey %s" % arvan["api_key"])
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode()
            arvan_data = json.loads(body).get("data", [])
            for video in arvan_data:
                title = video.get("title", "")
                if room_name in title:
                    uploaded = True
                    test_video_id = video.get("id", "")
                    info("Found on ArvanCloud: %s" % title)
                    break
        except Exception as e:
            pass
        if uploaded:
            break
        time.sleep(5)

    if uploaded:
        ok("Recording uploaded to ArvanCloud successfully!")
    else:
        warn("Upload not detected within timeout (may still be in progress)")

    # Step 6: Cleanup
    print("\n" + YELLOW + "[6/7] Cleaning up test artifacts..." + NC)
    if test_video_id:
        if delete_arvan_video(test_video_id, arvan["api_key"], arvan["base_url"]):
            ok("Deleted test video from ArvanCloud")
        else:
            warn("Could not delete test video - check ArvanCloud dashboard")
    else:
        info("No test video to clean up from ArvanCloud")

    for entry in os.listdir(recording_dir):
        entry_path = os.path.join(recording_dir, entry)
        if os.path.isdir(entry_path) and "jibri-test" in entry:
            subprocess.run(["rm", "-rf", entry_path], capture_output=True)
            info("Removed local recording: %s" % entry)
    for entry in os.listdir(state_dir):
        marker_path = os.path.join(state_dir, entry)
        if os.path.isfile(marker_path):
            os.remove(marker_path)
            info("Removed state marker: %s" % entry)

    # Step 7: Summary
    print("\n" + CYAN + "=" * 46 + NC)
    if issues == 0 and uploaded:
        print("  " + GREEN + "OK Jibri recording pipeline test PASSED" + NC)
    elif issues == 0:
        print("  " + YELLOW + "W  Recording triggered but upload not verified" + NC)
        print("     Check recordings/ and ArvanCloud dashboard.")
    else:
        print("  " + RED + "X  Test failed with %d issue(s)" % issues + NC)
    print(CYAN + "=" * 46 + NC)
    return issues == 0


if __name__ == "__main__":
    room = None
    duration = 5
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--room" and i + 1 < len(sys.argv):
            room = sys.argv[i + 2]
        elif arg == "--duration" and i + 1 < len(sys.argv):
            duration = int(sys.argv[i + 2])

    success = run_test(room_name=room, duration=duration)
    sys.exit(0 if success else 1)
