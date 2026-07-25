FROM jitsi/jibri:unstable

USER root

# Create av stub module  
RUN mkdir -p /opt/lightrec/av/audio /opt/lightrec/av/video /opt/lightrec/av/frame /opt/lightrec/av/packet

COPY av_stub/__init__.py /opt/lightrec/av/__init__.py

RUN for sub in frame audio; do \
  echo "from av_stub import AudioFrame, VideoFrame, Packet; Frame = AudioFrame" > /opt/lightrec/av/$sub/__init__.py; \
done && \
  echo "VideoCodecContext = type('VideoCodecContext', (), {}); VideoStream = type('VideoStream', (), {})" > /opt/lightrec/av/video/__init__.py && \
  echo "from av_stub import VideoFrame; VideoCodecContext = type('VideoCodecContext', (), {})" > /opt/lightrec/av/video/codeccontext.py && \
  echo "VideoStream = type('VideoStream', (), {})" > /opt/lightrec/av/video/stream.py

# Copy vendored aiortc + aioice from local
COPY vendor/aiortc /opt/lightrec/aiortc
COPY vendor/aioice /opt/lightrec/aioice
COPY vendor/pyee /opt/lightrec/pyee
COPY vendor/pylibsrtp /opt/lightrec/pylibsrtp
COPY vendor/ifaddr /opt/lightrec/ifaddr

# Copy lightrec
COPY lightrec.py /opt/lightrec/

ENV PYTHONPATH=/opt/lightrec

ENTRYPOINT ["python3", "-u", "/opt/lightrec/lightrec.py"]
