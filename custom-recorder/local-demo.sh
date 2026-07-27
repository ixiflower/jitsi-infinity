#!/usr/bin/env bash
# LightRec v3 — Run everything locally
set -euo pipefail
cd "$(dirname "$0")"

echo "=== LightRec v3 — Local Test Suite ==="
echo ""

# Ensure venv
if [ ! -d .venv ]; then
    echo "[setup] Creating venv..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q pytest
else
    source .venv/bin/activate
fi

echo "[1/2] Running 50 unit tests..."
python3 -m pytest test_lightrec_unit.py -v --tb=short 2>&1 | tail -10
echo ""

echo "[2/2] Running 17 e2e integration tests..."
python3 e2e_test.py
echo ""

echo "=== ✅ ALL TESTS PASS ==="
echo ""
echo "LightRec v3 is ready. Run it:        python3 custom-recorder/lightrec.py"
echo "Re-run tests:                         ./run_tests.sh"
echo ""
echo "What LightRec does end-to-end:"
echo "  XMPP connect → brewery join → wait JibriIq"
echo "  → join conference MUC → receive colibri IQ"
echo "  → write SDP → upgrade FFmpeg to real RTP"
echo "  → recording → on STOP, leave room, stop FFmpeg"
