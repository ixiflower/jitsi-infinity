# Jitsi Infinity

Jitsi Meet on Docker with custom Python auto-scaler — production-ready video conferencing stack with recording, monitoring, and auto-scaling.

Fully encrypted, 100% Open Source, Dockerized. Recording with Jibri, auto-scaling, and full monitoring stack.

---

## What Is This

This is a production-ready [Jitsi Meet](https://jitsi.org/jitsi-meet/) video conferencing deployment running entirely on Docker with Docker Compose.

It includes:

- Jitsi Web interface
- Prosody XMPP server
- Jicofo focus component
- JVB (video bridge)
- Jibri recording (multi-instance)
- **Custom Python auto-scaler**
- Prometheus + Grafana monitoring
- Portainer management
- File browser for recordings
- Optional add-ons

The deployment is customised with a hand-made Python auto-scaler (v2) that dynamically starts and stops Jibri recording containers based on real-time demand — no XMPP dependency, just HTTP + Docker API.

---

## Architecture

### Core Services

| Service | Container Name | Image | Port(s) |
|---|---|---|---|
| web | jitsi-web | jitsi/web | 8000, 8443 |
| prosody | jitsi-prosody | jitsi/prosody | 5222, 5280 |
| jicofo | jitsi-jicofo | jitsi/jicofo | 8888 |
| jvb | jitsi-jvb | jitsi/jvb | 10000/udp, 8080 |
| jibri-autoscaler | jitsi-jibri-autoscaler | (custom build) | — |
| jibri-N | jitsi-jibri-N | jitsi/jibri | — |

### Monitoring Stack

| Service | Port | Purpose |
|---|---|---|
| Prometheus | 9090 | Collects metrics from node_exporter |
| Grafana | 3000 | Visualizes metrics in dashboards |
| Portainer | 9000 | Docker container management UI |
| Filebrowser | 8081 | Browse & download recordings via web |
| Node Exporter | 9100 | System metrics (CPU, RAM, disk, network) |

### How They Connect

The autoscaler polls jicofo's REST API at `/stats` every N seconds. It checks how many Jibri recorders are available (idle) vs total registered. Based on configurable thresholds, it uses the Docker SDK to start or stop jibri containers by name.

### Optional Add-ons

- `jibri.yml` — Single jibri instance
- `jigasi.yml` — SIP gateway (audio calls)
- `transcriber.yml` — AI transcription
- `etherpad.yml` — Collaborative document editing
- `whiteboard.yml` — Excalidraw whiteboard
- `rtcstats.yml` — WebRTC stats & visualization
- `grafana.yml` — Grafana (standalone)
- `prometheus.yml` — Prometheus (standalone)

---

## Quick Start

```bash
# Clone or enter this directory
cd services

# Run the interactive setup
./setup.sh
```

The setup script will:
- Check for Docker & Docker Compose
- Create config directories
- Prompt for localhost or server mode
- Generate random passwords
- Write `.env` configuration
- Generate the jibri pool
- Start all services

### Manual Configuration

```bash
cp env.example .env
# edit .env with your settings
./generate-jibri-pool.sh
docker compose -f docker-compose.yml -f jibri-pool.yml up -d
```

Access your Jitsi instance at: `https://<your-server>:8443`

---

## Configuration

| Variable | Description |
|---|---|
| CONFIG | Path to persistent config directory |
| HTTP_PORT | HTTP port for web (default: 8000) |
| HTTPS_PORT | HTTPS port for web (default: 8443) |
| PUBLIC_URL | Public-facing URL of your instance |
| JVB_ADVERTISE_IPS | IP to advertise for JVB (set to server IP) |
| ENABLE_RECORDING | Enable Jibri recording (1 or 0) |
| ENABLE_LETSENCRYPT | Use Let's Encrypt (1 for domain, 0 for IP) |
| JIBRI_COUNT | Number of jibri instances to generate |
| JICOFO_ENABLE_REST | Enable jicofo REST API (required by autoscaler) |

---

## Auto-Scaler — Custom (v2)

**Location:** `jibri-autoscaler/main.py` (206 lines)
**Image:** Custom Docker image built from `jibri-autoscaler/Dockerfile`
**Language:** Python 3
**Dependencies:** `docker` SDK + `requests` library

### How It Works (English)

The autoscaler is a lightweight Python daemon that runs inside a Docker container. It has access to the Docker daemon via `/var/run/docker.sock` and communicates with jicofo's REST API to make scaling decisions.

**Step 1 — POLL:** Every N seconds (default: 15), it fetches `http://jicofo:8888/stats`. The response contains:

```json
{
  "jibri_detector": {
    "count": 5,
    "available": 2
  }
}
```

- `count` = total jibris registered in the MUC
- `available` = jibris currently idle and ready to record

**Step 2 — DECIDE:** Based on the stats and the number of running containers, the autoscaler chooses one of three actions:

1. **Initial boot:** If zero containers are running, start `MIN_IDLE + 1` containers
2. **Scale up:** If `available < MIN_IDLE` and `running < MAX_TOTAL`, start one stopped container
3. **Scale down:** If `available > MIN_IDLE` and `running > MIN_IDLE`, find the highest-numbered running container that is NOT in the hot pool (1..MIN_IDLE). If it has been idle for longer than `IDLE_TIMEOUT`, stop it

**Step 3 — REPEAT:** Loop forever with a sleep of `POLL_INTERVAL` seconds.

### Decision Logic (Pseudocode)

```
loop:
    sleep(POLL_INTERVAL)
    stats = fetch_jicofo_stats()
    running = docker.list_containers(prefix)

    if running == 0:
        start(MIN_IDLE + 1 containers)       # initial boot

    elif stats.available < MIN_IDLE and len(running) < MAX_TOTAL:
        start(one stopped container)          # scale up

    elif stats.available > MIN_IDLE and len(running) > MIN_IDLE:
        candidate = highest_numbered_running_not_in_hot_pool()
        if candidate has been idle > IDLE_TIMEOUT:
            stop(candidate)                   # scale down
```

### Configuration Variables

| Variable | Default | Description |
|---|---|---|
| JICOFO_URL | http://jicofo:8888/stats | jicofo REST API endpoint |
| AUTOSCALER_POLL_INTERVAL | 15 | Seconds between polls |
| AUTOSCALER_MIN_IDLE | 1 | Minimum idle jibris to keep |
| AUTOSCALER_MAX_TOTAL | 20 | Maximum total jibri containers |
| AUTOSCALER_IDLE_TIMEOUT | 300 | Seconds before stopping idle jibri (5 minutes) |
| AUTOSCALER_CONTAINER_PREFIX | jitsi-jibri- | Prefix for jibri container names |

### Scaling Behavior

| Scenario | Action |
|---|---|
| First boot (no jibris running) | Start MIN_IDLE + 1 containers |
| Available jibris < MIN_IDLE | Start one stopped container |
| Available jibris > MIN_IDLE (sustained for > IDLE_TIMEOUT) | Stop highest-numbered container that has been idle > IDLE_TIMEOUT |
| Running == MAX_TOTAL | Cannot scale up (at capacity) |
| Running == MIN_IDLE | Cannot scale down (minimum guaranteed) |

> **Note:** The first MIN_IDLE containers (1..MIN_IDLE) are NEVER stopped. They form the "hot pool" — always ready to record immediately. Only excess containers beyond that are scaled down.

### Why This Approach

Instead of using the official Jitsi autoscaler (which requires Kubernetes, Google Cloud, or complex setup), this custom scaler:

- Runs entirely inside Docker — no external dependencies
- Uses simple HTTP polling — no XMPP knowledge needed
- Starts/stops containers via Docker SDK — no orchestration needed
- Configurable via environment variables — no code changes
- Lightweight — single Python file, minimal resource usage
- Predictable — deterministic scaling logic, no ML/heuristics

Perfect for small to medium Jitsi deployments where you want recording on-demand without paying for idle jibri containers 24/7.

---

### نحوه عملکرد اسکیلر خودکار (فارسی)

این یک اسکیلر خودکار (Auto-scaler) است که به صورت دستی با پایتون نوشته شده و وظیفه‌اش مدیریت خودکار کانتینرهای ضبط جیبری (Jibri) بر اساس نیاز واقعی است.

**نحوه کار:**

۱. هر ۱۵ ثانیه یک بار از jicofo آمار می‌گیرد:
   - چند تا جیبری در دسترس (available) هستند
   - چند تا جیبری در مجموع (count) ثبت نام کرده‌اند

۲. تصمیم‌گیری بر اساس سه حالت:

   - **بوت اولیه:** اگر هیچ کانتینری در حال اجرا نباشد، به اندازه MIN_IDLE + 1 کانتینر شروع می‌کند.
   - **افزایش (Scale Up):** اگر جیبری‌های در دسترس از حد MIN_IDLE کمتر باشد و تعداد کل از MAX_TOTAL کمتر باشد، یک کانتینر متوقف شده را شروع می‌کند.
   - **کاهش (Scale Down):** اگر جیبری‌های در دسترس بیشتر از MIN_IDLE باشد و یک کانتینر اضافه برای بیش از IDLE_TIMEOUT (۵ دقیقه) بیکار مانده باشد، آن را متوقف می‌کند.

**ویژگی‌های مهم:**

- کاملاً داخل داکر اجرا می‌شود — نیاز به سرویس خارجی ندارد
- از HTTP ساده استفاده می‌کند — نیازی به XMPP نیست
- کانتینرها را با Docker SDK شروع/متوقف می‌کند
- از طریق متغیرهای محیطی (Environment Variables) قابل تنظیم است
- بسیار سبک — یک فایل پایتون ساده
- کانتینرهای ۱ تا MIN_IDLE هرگز متوقف نمی‌شوند (استخر آماده)

**متغیرهای قابل تنظیم:**

| متغیر | توضیح |
|---|---|
| JICOFO_URL | آدرس API جیکوفو |
| AUTOSCALER_POLL_INTERVAL | فاصله بین هر بار چک کردن (ثانیه) |
| AUTOSCALER_MIN_IDLE | حداقل جیبری بیکار آماده |
| AUTOSCALER_MAX_TOTAL | حداکثر تعداد کل جیبری‌ها |
| AUTOSCALER_IDLE_TIMEOUT | مهلت بیکاری قبل از توقف (ثانیه) |
| AUTOSCALER_CONTAINER_PREFIX | پیشوند نام کانتینرها |

---

## Generating the Jibri Pool

The `generate-jibri-pool.sh` script reads `JIBRI_COUNT` from `.env` and generates `jibri-pool.yml` with that many jibri services.

Each jibri instance gets:
- Its own container name: `jitsi-jibri-N`
- Its own config volume: `$CONFIG/jibri-N`
- An instance ID: `JIBRI_INSTANCE_ID=N`
- 2GB shared memory (`shm_size: 2gb`)
- SYS_ADMIN capability (required for Chrome/recording)

To change the pool size:

1. Edit `.env`: `JIBRI_COUNT=<new_number>`
2. Run: `./generate-jibri-pool.sh`

---

## Building Images

Use the Makefile to build Docker images:

| Command | Description |
|---|---|
| `make all` | Build all services locally |
| `make release` | Multi-arch buildx (amd64 + arm64) |
| `make build_<service>` | Build a single service |
| `make buildx_<service>` | Build multi-arch for a single service |
| `make tag` | Tag an image |
| `make push` | Push an image to DockerHub |
| `make clean` | Stop & remove all containers |
| `make prepare` | Force rebuild all (no cache) |

Services that can be built: base, base-java, web, prosody, jicofo, jvb, jigasi, jibri

---

## Directory Structure

```
services/
├── .env                          # Main configuration
├── .env.jibri                    # Jibri per-container environment
├── docker-compose.yml            # Main compose file
├── jibri-pool.yml                # Auto-generated jibri instances
├── generate-jibri-pool.sh        # Script to regenerate jibri pool
├── setup.sh                      # Interactive setup script
├── Makefile                      # Build automation
│
├── jibri-autoscaler/             # Custom auto-scaler (Python)
│   ├── Dockerfile
│   └── main.py                   # Scaling logic (206 lines)
│
├── config/                       # Runtime configuration
│   ├── jibri-{1..N}/             # Per-instance config + logs
│   ├── jicofo/
│   ├── jvb/
│   ├── prosody/
│   └── web/
│
├── jibri/                        # Jibri Docker image source
├── jicofo/                       # Jicofo Docker image source
├── jvb/                          # JVB Docker image source
├── prosody/                      # Prosody Docker image source
├── web/                          # Web Docker image source
├── base/                         # Base Docker image
├── base-java/                    # Java base Docker image
│
├── grafana/                      # Grafana provisioning
├── prometheus/                   # Prometheus config
├── log-analyser/                 # Loki + OTEL config
├── rtcstats/                     # WebRTC stats
│
├── recordings/                   # Recordings storage
├── resources/                    # Images and icons
└── examples/                     # Example configs
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Jibri containers crash on startup | Ensure `shm_size: 2gb` is set and `SYS_ADMIN` capability is added. Check logs: `docker compose logs jibri-1` |
| Autoscaler not scaling | Ensure `JICOFO_ENABLE_REST=1` in `.env`. Check autoscaler logs: `docker compose logs jibri-autoscaler`. Verify jicofo stats: `curl http://localhost:8888/stats` |
| Can't connect to Jitsi Meet | Check firewall: ports 8000/tcp, 8443/tcp, 10000/udp must be open. Verify `PUBLIC_URL` is correct. Check nginx logs: `docker compose logs web` |
| Recording not working | Check `.env.jibri` has correct XMPP credentials. Verify jibri can reach prosody. Check chromium flags in `config/jibri-1/config.json` |

---

## Useful Commands

```bash
# View all running services
docker compose -f docker-compose.yml -f jibri-pool.yml ps

# View autoscaler logs (follow)
docker compose logs -f jibri-autoscaler

# View jibri logs
docker compose logs -f jibri-1

# Restart the autoscaler
docker compose up -d --force-recreate jibri-autoscaler

# Scale jibri pool (edit .env first, then regenerate)
# vi .env -> change JIBRI_COUNT
# ./generate-jibri-pool.sh

# Stop everything
docker compose -f docker-compose.yml -f jibri-pool.yml down

# Access jicofo stats
curl http://localhost:8888/stats
```

---

## License

Apache License 2.0 — see `LICENSE` file for details.

[Jitsi Meet](https://jitsi.org/) | [Docker](https://docker.com)
