#!/usr/bin/env python3
"""
av compatibility stub — provides AudioFrame/VideoFrame stubs that aiortc needs.
Replaces the real av library when running on systems with mismatched ffmpeg.
"""
import ctypes, os, logging

log = logging.getLogger("av.stub")

# Find native libs
lib_dir = os.environ.get("LIGHTREC_NATIVE_LIB", "")
if not lib_dir:
    # Try common paths
    for p in ["/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu"]:
        if os.path.exists(f"{p}/libavformat.so"):
            lib_dir = p
            break

if lib_dir:
    for lib in ["libavformat.so", "libavcodec.so", "libavutil.so",
                "libswscale.so", "libswresample.so"]:
        path = f"{lib_dir}/{lib}"
        if os.path.exists(path):
            try:
                ctypes.CDLL(path, ctypes.RTLD_GLOBAL)
            except:
                pass

class AudioFrame:
    """Stub for av.AudioFrame."""
    format = "s16"
    layout = "stereo"
    sample_rate = 48000
    samples = 1024
    pts = 0
    time_base = (1, 48000)
    
    def __init__(self, format="s16", layout="stereo", samples=1024):
        self.format = format
        self.layout = layout
        self.samples = samples
    
    def to_ndarray(self):
        import numpy as np
        return np.zeros((self.samples, 2), dtype=np.int16)

class VideoFrame:
    """Stub for av.VideoFrame."""
    width = 1280
    height = 720
    format = "yuv420p"
    pts = 0
    time_base = (1, 30)
    
    def __init__(self, width=1280, height=720, format="yuv420p"):
        self.width = width
        self.height = height
        self.format = format
    
    def to_ndarray(self):
        import numpy as np
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
    
    def reformat(self, width=None, height=None, format=None):
        return VideoFrame(
            width or self.width,
            height or self.height,
            format or self.format
        )

class Packet:
    """Stub for av.Packet."""
    pass

class CodecContext:
    """Stub for av.CodecContext."""
    pass
