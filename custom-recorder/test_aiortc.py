#!/usr/bin/env python3
"""Test which parts of aiortc work without av library."""
import sys, importlib

# Modules that don't need av
tests = {
    "aioice": "ICE",
    "aiortc.rtp": "RTP",
    "aiortc.sdp": "SDP",
    "aiortc.codecs": "Codecs",
}

for mod, name in tests.items():
    try:
        importlib.import_module(mod)
        print(f"{name}: OK")
    except Exception as e:
        print(f"{name}: FAIL - {e}")

# Test the main aiortc import
try:
    import aiortc
    print(f"aiortc full: OK (version {aiortc.__version__})")
except Exception as e:
    print(f"aiortc full: FAIL - {e}")
    # Check which submodule fails
    import traceback
    traceback.print_exc()
