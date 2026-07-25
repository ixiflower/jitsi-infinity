FROM python:3.12-slim

WORKDIR /opt/lightrec

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>&1 | tail -3

# Copy source
COPY lightrec.py /opt/lightrec/

ENTRYPOINT ["python3", "-u", "/opt/lightrec/lightrec.py"]
