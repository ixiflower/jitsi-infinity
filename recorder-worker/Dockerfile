# LightRec Recorder Worker — Chromium + FFmpeg
FROM archlinux:latest

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm \
    chromium \
    ffmpeg \
    xorg-server-xvfb \
    pulseaudio \
    python3 \
    && yes | pacman -Scc

RUN useradd -m -G audio,video recorder

WORKDIR /home/recorder

COPY record.sh /usr/local/bin/record.sh
RUN chmod +x /usr/local/bin/record.sh

CMD ["/usr/local/bin/record.sh"]
