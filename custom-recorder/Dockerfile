# LightRec v3 — Multi-stage build with static FFmpeg
FROM mwader/static-ffmpeg:7.1 AS ffmpeg

FROM python:3.11-slim

COPY --from=ffmpeg /ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /ffprobe /usr/local/bin/ffprobe
RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

RUN adduser --disabled-password --gecos "" lightrec && \
    mkdir -p /recordings && \
    chown lightrec:lightrec /recordings

COPY --chown=lightrec:lightrec lightrec.py /opt/lightrec.py
RUN chmod +x /opt/lightrec.py

USER lightrec
WORKDIR /opt

CMD ["python3", "-u", "/opt/lightrec.py"]
