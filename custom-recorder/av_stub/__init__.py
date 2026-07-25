#!/usr/bin/env python3
"""Full av stub with all submodules aiortc needs."""

class AudioFrame:
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

class VideoFrame:
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
        raise RuntimeError("av stub: numpy not available")
    def reformat(self, width=None, height=None, format="yuv420p"):
        return VideoFrame(width or self.width, height or self.height, format)

class Packet:
    def __init__(self):
        self.data = b""
        self.pts = 0
        self.dts = 0
        self.time_base = (1, 1000)

class CodecContext:
    pass

class AudioResampler:
    pass

class AudioCodecContext:
    pass

class Frame:
    pass

# Export audio/video submodules
class _Audio:
    class AudioStream:
        pass

class _Video:
    class VideoCodecContext:
        pass
    class VideoStream:
        pass
    class codeccontext:
        VideoCodecContext = VideoCodecContext
    class stream:
        VideoStream = type("VideoStream", (), {})

audio = _Audio()
video = _Video()
frame = type("frame", (), {"Frame": Frame})()
packet = type("packet", (), {"Packet": Packet})()

__all__ = [
    "AudioFrame", "VideoFrame", "Packet", "CodecContext",
    "AudioResampler", "AudioCodecContext", "Frame",
    "audio", "video", "frame", "packet",
]
