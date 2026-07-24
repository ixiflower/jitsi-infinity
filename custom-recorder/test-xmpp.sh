#!/bin/bash
# Test LightRec XMPP client on the server using jitsi/jibri image which has Python3
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JITSI_DIR="$(dirname "$SCRIPT_DIR")"

# Copy xmpp_client.py to server
sshpass -p '!!kg$%RWof!d%N4' scp -o StrictHostKeyChecking=no \
  "$SCRIPT_DIR/xmpp_client.py" \
  "$SCRIPT_DIR/requirements.txt" \
  ubuntu@37.32.20.70:/tmp/lightrec/

# Run on the server inside a jibri container (has Python3 + Docker network access)
sshpass -p '!!kg$%RWof!d%N4' ssh -o StrictHostKeyChecking=no ubuntu@37.32.20.70 '
mkdir -p /tmp/lightrec

# Create a Dockerfile that installs slixmpp
cat > /tmp/lightrec/Dockerfile << "EOF"
FROM jitsi/jibri:unstable
RUN apt-get update -qq && apt-get install -y -qq python3-pip 2>/dev/null; pip3 install slixmpp -q
COPY xmpp_client.py /opt/lightrec/xmpp_client.py
COPY requirements.txt /opt/lightrec/requirements.txt
ENTRYPOINT ["python3", "/opt/lightrec/xmpp_client.py"]
EOF

# Build and run
cd /tmp/lightrec
docker build -t lightrec-test -f Dockerfile . 2>&1 | tail -3

# Run with access to jitsi network
docker run --rm --network jitsi-infinity_meet.jitsi \
  -v /home/ubuntu/jitsi-infinity/.env.jibri:/app/.env.jibri:ro \
  -e LIGHTREC_ROOM=lightrec-test \
  --name lightrec-test \
  lightrec-test 2>&1
' 2>&1