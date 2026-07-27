#!/usr/bin/env bash
# LightRec v3 — Real-time pipeline monitor
# Run in a separate terminal while testing recording
cd "$(dirname "$0")"
echo "═══════════════════════════════════════════════════════════════"
echo "  LightRec v3 Pipeline Monitor — watching live logs"
echo "  Open http://localhost:8000 in browser, start a meeting,"
echo "  click Record, and watch each step here"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

docker logs -f jitsi-lightrec 2>&1 | while read line; do
  case "$line" in
    *"STEP 1/10"*) echo -e "${CYAN}[CONNECT]${NC} $line" ;;
    *"STEP 2/10"*) echo -e "${CYAN}[TLS]${NC} $line" ;;
    *"STEP 3/10"*) echo -e "${CYAN}[AUTH]${NC} $line" ;;
    *"STEP 4/10"*) echo -e "${CYAN}[BIND]${NC} $line" ;;
    *"STEP 5/10"*) echo -e "${CYAN}[BREWERY]${NC} $line" ;;
    *"STEP 6/10"*) echo -e "${YELLOW}[JIBRI_IQ]${NC} $line" ;;
    *"ACK sent"*) echo -e "${GREEN}[ACK]${NC} $line" ;;
    *"STEP 7/10"*) echo -e "${YELLOW}[UPGRADE]${NC} $line" ;;
    *"STEP 8/10"*) echo -e "${YELLOW}[COLIBRI]${NC} $line" ;;
    *"STEP 9/10"*) echo -e "${GREEN}[RTP]${NC} $line" ;;
    *"STEP 10/10"*) echo -e "${RED}[STOP]${NC} $line" ;;
    *"✅"*)        echo -e "${GREEN}[OK]${NC} $line" ;;
    *"❌"*)        echo -e "${RED}[FAIL]${NC} $line" ;;
    *"Ready for recording triggers"*) echo -e "${GREEN}[READY]${NC} ✅ Connected to brewery, waiting for Record click..." ;;
    *) echo "$line" ;;
  esac
done
