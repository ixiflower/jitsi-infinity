#!/bin/bash
# Jirecon launcher for Jitsi Infinity
# Reuses the jitsi/jibri Docker image for Java runtime
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/config/jirecon"
RECORDING_DIR="${SCRIPT_DIR}/recordings"

mkdir -p "${CONFIG_DIR}" "${RECORDING_DIR}"

# Read credentials from .env.jibri
RECORDER_PASS=$(grep -E "^JIBRI_RECORDER_PASSWORD=" "${SCRIPT_DIR}/.env.jibri" 2>/dev/null | cut -d= -f2-)
XMPP_DOMAIN=$(grep -E "^XMPP_DOMAIN=" "${SCRIPT_DIR}/.env.jibri" 2>/dev/null | cut -d= -f2-)
XMPP_DOMAIN="${XMPP_DOMAIN:-meet.jitsi}"

# Generate jirecon.properties
cat > "${CONFIG_DIR}/jirecon.properties" << EOF
org.jitsi.impl.neomedia.transform.dtls.DtlsPacketTransformer.dropUnencryptedPkts=true
org.jitsi.jirecon.JIRECON_NICKNAME=jirecon
org.jitsi.jirecon.MAX_STREAM_PORT=10000
org.jitsi.jirecon.MIN_STREAM_PORT=8000
org.jitsi.jirecon.OUTPUT_DIR=${RECORDING_DIR}
org.jitsi.jirecon.XMPP_HOST=xmpp.meet.jitsi
org.jitsi.jirecon.XMPP_PORT=5222
org.jitsi.jirecon.XMPP_USER=recorder@hidden.meet.jitsi
org.jitsi.jirecon.XMPP_PASS=${RECORDER_PASS}
EOF

echo "Jirecon config written to ${CONFIG_DIR}/jirecon.properties"
echo ""
echo "To record a room, run:"
echo "  docker run --rm -v ${CONFIG_DIR}:/config -v ${RECORDING_DIR}:/recordings \\"
echo "    --network jitsi-infinity_meet.jitsi \\"
echo "    --entrypoint bash jitsi/jibri:unstable -c \\"
echo "      'java -cp /opt/jirecon/jirecon.jar:/opt/jirecon/lib/* \\"
echo "        org.jitsi.jirecon.Main --conf=/config/jirecon.properties \\"
echo "        --time=60 ROOM@muc.meet.jitsi'"
echo ""
echo "OR use the service definition in jirecon.yml (docker compose -f jirecon.yml up -d)"
