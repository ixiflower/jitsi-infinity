#!/usr/bin/env bash
# deploy-lightrec.sh — Deploy LightRec v3 orchestrator to Jitsi Infinity server
# Run this ON the server (37.32.20.70) from the jitsi-infinity directory.
#
# Usage:
#   ssh ubuntu@37.32.20.70 'bash -s' < deploy-lightrec.sh
#   (run from ~/jitsi-infinity on the server)

set -euo pipefail
cd "$(dirname "$0")"

echo "=== LightRec v3 Deployment ==="

# 1. Create config directory
mkdir -p "${CONFIG:-~/.jitsi-meet-cfg}/lightrec"

# 2. Build the LightRec image
echo "Building LightRec image..."
docker compose -f docker-compose.yml -f custom-recorder/docker-compose.lightrec.yml build lightrec

# 3. Stop any existing LightRec
echo "Stopping any existing LightRec..."
docker compose -f docker-compose.yml -f custom-recorder/docker-compose.lightrec.yml rm -sf lightrec 2>/dev/null || true

# 4. Start LightRec
echo "Starting LightRec..."
docker compose -f docker-compose.yml -f custom-recorder/docker-compose.lightrec.yml up -d lightrec

# 5. Wait for startup and check logs
echo "Waiting 5 seconds for startup..."
sleep 5
docker logs jitsi-lightrec --tail 30

# 6. Verify it connected to the brewery
echo ""
echo "=== Checking brewery presence ==="
docker exec jitsi-lightrec python3 -c "
import socket, ssl, base64, os, time, uuid
# Quick check: connect and see who's in the brewery
pw = os.environ.get('JIBRI_XMPP_PASSWORD', '')
s = socket.create_connection(('xmpp.meet.jitsi', 5222), timeout=10)
def r(m, t=5):
    s.settimeout(t); d=b''
    while m not in d: c=s.recv(4096); d+=c if c else b''; break
    return d
s.send(b\"<stream:stream to='auth.meet.jitsi' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>\")
r(b'</stream:features>')
s.send(b\"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>\")
s.recv(4096)
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
s=ctx.wrap_socket(s, server_hostname='xmpp.meet.jitsi')
s.send(b\"<stream:stream to='auth.meet.jitsi' ...>\")
r(b'</stream:features>')
auth=b'\\x00jibri\\x00'+pw.encode()
s.send(f'<auth ... mechanism=PLAIN>{base64.b64encode(auth).decode()}</auth>'.encode())
r(b'<success',10)
s.send(b\"<stream:stream to='auth.meet.jitsi' ...>\")
r(b'</stream:features>')
s.send(b\"<iq id='b1' type='set'><bind><resource>check</resource></bind></iq>\")
time.sleep(0.5); s.recv(8192)
s.send(b\"<iq id='s1' type='set'><session/></iq>\")
time.sleep(0.5); s.recv(8192)
s.send(b\"<presence to='jibribrewery@internal-muc.meet.jitsi/check'><x xmlns='http://jabber.org/protocol/muc'/></presence>\")
time.sleep(3)
d=b''
s.settimeout(3)
try:
    while True: d+=s.recv(65536)
except: pass
# Count Jibri instances
jibri_count = d.count(b'busy-status')
lightrec_count = d.count(b'lightrec')
print(f'Jibri instances in brewery: {jibri_count}')
print(f'LightRec detected: {\"YES\" if lightrec_count else \"NO\"} (count={lightrec_count})')
if lightrec_count:
    print('✅ LightRec is visible in brewery!')
else:
    print('⚠️ LightRec not detected in brewery')
s.send(b'</stream:stream>'); s.close()
"

echo ""
echo "=== Deployment Summary ==="
echo "✅ LightRec v3 deployed"
echo "   Container: jitsi-lightrec"
echo "   Logs: docker logs jitsi-lightrec -f"
echo "   Test: click Record in a Jitsi meeting and check"
echo "         docker logs jitsi-lightrec --tail 20"
