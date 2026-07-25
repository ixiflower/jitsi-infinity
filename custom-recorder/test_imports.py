#!/usr/bin/env python3
"""Test av stub + aiortc import works with vendored packages."""
import os, sys

# Make sure we find our vendored packages
sys.path.insert(0, "/opt/vendor")
sys.path.insert(0, "/opt")

# Build the av module directly (no need for __init__.py files)
import types

# Create av module
av = types.ModuleType("av")

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
        raise RuntimeError("numpy not available")
    def reformat(self, width=None, height=None, format="yuv420p"):
        return VideoFrame(width or self.width, height or self.height, format)

class Packet:
    pass

class CodecContext:
    pass

av.AudioFrame = AudioFrame
av.VideoFrame = VideoFrame
av.Packet = Packet
av.CodecContext = CodecContext

# Create submodules
av_frame = types.ModuleType("av.frame")
av_frame.Frame = type("Frame", (), {})
sys.modules["av.frame"] = av_frame

av_packet = types.ModuleType("av.packet")
av_packet.Packet = Packet
sys.modules["av.packet"] = av_packet

av_audio = types.ModuleType("av.audio")
av_audio.AudioStream = type("AudioStream", (), {})
sys.modules["av.audio"] = av_audio

av_video = types.ModuleType("av.video")
av_video.VideoCodecContext = type("VideoCodecContext", (), {})
av_video.VideoStream = type("VideoStream", (), {})
sys.modules["av.video"] = av_video

av_video_cc = types.ModuleType("av.video.codeccontext")
av_video_cc.VideoCodecContext = type("VideoCodecContext", (), {})
sys.modules["av.video.codeccontext"] = av_video_cc

av_video_stream = types.ModuleType("av.video.stream")
av_video_stream.VideoStream = type("VideoStream", (), {})
sys.modules["av.video.stream"] = av_video_stream

av_container = types.ModuleType("av.container")
av_container.open = lambda *a, **kw: None
sys.modules["av.container"] = av_container

sys.modules["av"] = av

# Now try importing aiortc
print("Importing aiortc...")
import aiortc
print(f"aiortc {aiortc.__version__}: OK")

# Test RTP module
print("Importing aiortc.rtp...")
from aiortc.rtp import RtpPacket, RtpPacketizer
print("RTP OK")

# Test SDP
print("Importing aiortc.sdp...")  
from aiortc.sdp import SessionDescription
print("SDP OK")

print("\nAll imports PASS!")
