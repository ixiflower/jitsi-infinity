FROM python:3.12-slim

WORKDIR /opt/lightrec

# Install dependencies  
RUN pip install --no-cache-dir slixmpp aiortc aiohttp ffmpeg-python

# Copy the recorder modules
COPY xmpp_client.py /opt/lightrec/

ENTRYPOINT ["python3", "/opt/lightrec/xmpp_client.py"]
