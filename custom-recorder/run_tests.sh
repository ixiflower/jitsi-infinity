#!/usr/bin/env bash
# LightRec local test suite
set -e
cd "$(dirname "$0")"

# Activate or create venv
if [ ! -d .venv ]; then
    python3 -m venv .venv
    . .venv/bin/activate
    pip install pytest -q 2>/dev/null || true
else
    . .venv/bin/activate
fi

echo "═══════════════════════════════════════"
echo "  1) Unit tests (50 tests)"
echo "═══════════════════════════════════════"
python3 -m pytest test_lightrec_unit.py -v --tb=short || true

echo
echo "═══════════════════════════════════════"
echo "  2) E2E integration test"
echo "═══════════════════════════════════════"
python3 e2e_test.py || true

echo
echo "═══════════════════════════════════════"
echo "  Done!"
echo "═══════════════════════════════════════"
