<p align="center">
  <img src="resources/jitsi-docker.png" alt="Jitsi Infinity" width="200"/>
</p>

<h1 align="center">🚀 Jitsi Infinity</h1>

<p align="center">
  <b>Jitsi Meet on Docker</b> — <i>Production-ready video conferencing stack</i>
  <br>
  <b>Custom Python Auto-Scaler</b> · <b>Multi-Instance Recording</b> · <b>Full Monitoring</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square" alt="Python"/>
  <img src="https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker" alt="Docker"/>
  <img src="https://img.shields.io/badge/jitsi-meet-00B4A0?style=flat-square" alt="Jitsi"/>
  <img src="https://img.shields.io/badge/status-stable-brightgreen?style=flat-square" alt="Status"/>
</p>

---

## 📋 Table of Contents

- [What Is This](#-what-is-this)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Auto-Scaler](#-auto-scaler--custom-v2)
- [ArvanCloud Upload](#-arvancloud-vod-auto-upload)
- [Persian Documentation](#-persian-documentation)
- [Generating the Jibri Pool](#-generating-the-jibri-pool)
- [Building Images](#-building-images)
- [Directory Structure](#-directory-structure)
- [Troubleshooting](#-troubleshooting)
- [Useful Commands](#-useful-commands)
- [License](#-license)

---

## 🎯 What Is This

A production-ready **Jitsi Meet** deployment running entirely on Docker with:

| 🔴 Core | 🎥 Recording | 📊 Monitoring | 🛠 Management |
|---|---|---|---|
| Jitsi Web | Jibri multi-instance | Prometheus | Portainer |
| Prosody XMPP | Custom Python auto-scaler | Grafana | Filebrowser |
| Jicofo focus | Pool management (1..N) | Node Exporter | — |
| JVB bridge | Hot-standby pool | — | — |

Deploy your own secure, scalable video conferencing platform with recording on-demand — without Kubernetes or complex infrastructure.

---

## 🏗 Architecture

### Service Map

```
                     ┌─────────────────────┐
                     │      WEB (nginx)     │
                     │   :8000 / :8443      │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │   PROSODY (XMPP)     │
                     │   :5222 / :5280      │
                     └──────────┬──────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
   ┌──────────▼──────────┐     │     ┌────────────▼────────────┐
   │   JICOFO (focus)    │     │     │   JVB (video bridge)    │
   │   :8888/stats       │◄────┘     │   :10000/udp            │
   └──────────┬──────────┘           └─────────────────────────┘
              │
              │ HTTP polling (every 15s)
              ▼
   ┌─────────────────────────────────────────────────────┐
   │              JIBRI AUTO-SCALER (Python)              │
   │  ┌───────────────────────────────────────────────┐  │
   │  │  Polls: available < MIN_IDLE  →  Scale UP     │  │
   │  │  Polls: excess idle > TIMEOUT →  Scale DOWN   │  │
   │  │  Docker API → start/stop containers           │  │
   │  └───────────────────────┬───────────────────────┘  │
   └──────────────────────────┼──────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │  jibri-1    │   │  jibri-2    │   │  jibri-3    │
    │  recorder   │   │  recorder   │   │  recorder   │
    └─────────────┘   └─────────────┘   └─────────────┘
```

### Monitoring Stack

```
    ┌──────────────┐     ┌──────────────┐     ┌────────────────┐
    │  Prometheus  │────▶│   Grafana    │     │   Portainer    │
    │  :9090       │     │  :3000       │     │  :9000         │
    └──────┬───────┘     └──────────────┘     └────────────────┘
           │
    ┌──────▼───────┐     ┌──────────────┐
    │Node Exporter │     │ Filebrowser  │
    │  :9100       │     │  :8081       │
    └──────────────┘     └──────────────┘
```

---

## 🚀 Quick Start

```bash
# 1. Clone and enter the directory
cd services

# 2. Run the interactive setup
./setup.sh
```

The setup script will:
- ✅ Check for Docker & Docker Compose
- ✅ Create config directories
- ✅ Prompt for localhost or server mode
- ✅ Generate random passwords
- ✅ Write `.env` configuration
- ✅ Generate the jibri pool
- ✅ Start all services

### Manual Setup

```bash
cp env.example .env
# edit .env with your settings
./generate-jibri-pool.sh
docker compose -f docker-compose.yml -f jibri-pool.yml up -d
```

> 🌐 Access your instance at: **`https://<your-server>:8443`**

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `CONFIG` | `/home/ubuntu/.jitsi-meet-cfg` | Path to persistent config directory |
| `HTTP_PORT` | `8000` | HTTP port for web |
| `HTTPS_PORT` | `8443` | HTTPS port for web |
| `PUBLIC_URL` | — | Public-facing URL of your instance |
| `JVB_ADVERTISE_IPS` | — | IP to advertise for JVB |
| `ENABLE_RECORDING` | `1` | Enable Jibri recording |
| `ENABLE_LETSENCRYPT` | `0` | Use Let's Encrypt (1 for domain) |
| `JIBRI_COUNT` | `3` | Number of jibri instances |
| `JICOFO_ENABLE_REST` | `1` | Enable jicofo REST API |
| `ARVAN_API_KEY` | — | ArvanCloud VOD API key for auto-upload |
| `ARVAN_CHANNEL_ID` | — | Target ArvanCloud channel ID |
| `ARVAN_VOD_BASE_URL` | `https://napi.arvancloud.ir/vod/2.0` | ArvanCloud VOD API base URL |

---

## 🤖 Auto-Scaler — Custom (v2)

```
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║      █████  ██    ██ ████████  ██████    ██████              ║
  ║     ██   ██ ██    ██    ██    ██    ██  ██    ██             ║
  ║     ███████ ██    ██    ██    ██    ██  ██    ██             ║
  ║     ██   ██ ██    ██    ██    ██    ██  ██    ██             ║
  ║     ██   ██  ██████     ██     ██████    ██████              ║
  ║                                                              ║
  ║              🐍 Python  ·  🐳 Docker SDK                     ║
  ║              📍 jibri-autoscaler/main.py  (206 lines)        ║
  ╚══════════════════════════════════════════════════════════════╝
```

### How It Works

A lightweight Python daemon that runs inside a Docker container with access to the Docker socket. It polls jicofo's REST API every N seconds and makes scaling decisions.

#### Step 1 — Poll

```bash
$ curl http://jicofo:8888/stats
# Response:
# {
#   "jibri_detector": {
#     "count": 5,        # total jibris registered
#     "available": 2     # jibris currently idle
#   }
# }
```

#### Step 2 — Decide

```
  ┌─► SLEEP 15s ──► FETCH STATS ──► running == 0?
  │                                      │
  │                                  YES │
  │                                      ▼
  │                              START MIN_IDLE+1
  │                                      │
  │                                      │ NO
  │                                      ▼
  │                              available < MIN_IDLE
  │                              AND running < MAX_TOTAL?
  │                                      │
  │                                  YES │
  │                                      ▼
  │                              START one stopped container
  │                                      │
  │                                      │ NO
  │                                      ▼
  │                              available > MIN_IDLE
  │                              AND running > MIN_IDLE?
  │                                      │
  │                                  YES │
  │                                      ▼
  │                              idle > TIMEOUT?
  │                                      │
  │                                  YES │
  │                                      ▼
  │                              STOP candidate
  │                                      │
  └──────────────────────────────────────┘
```

#### Step 3 — Repeat

The loop runs forever, sleeping `POLL_INTERVAL` seconds between iterations.

### Configuration Variables

| Variable | Default | Description |
|---|---|---|
| `JICOFO_URL` | `http://jicofo:8888/stats` | jicofo REST API endpoint |
| `AUTOSCALER_POLL_INTERVAL` | `15` | Seconds between polls |
| `AUTOSCALER_MIN_IDLE` | `1` | Minimum idle jibris to keep |
| `AUTOSCALER_MAX_TOTAL` | `20` | Maximum total jibri containers |
| `AUTOSCALER_IDLE_TIMEOUT` | `300` | Seconds before stopping idle jibri |
| `AUTOSCALER_CONTAINER_PREFIX` | `jitsi-jibri-` | Container name prefix |

### Scaling Scenarios

| Scenario | Action |
|---|---|
| 🟢 **First boot** (no jibris running) | Start `MIN_IDLE + 1` containers |
| 🔼 **Scale up** (available < MIN_IDLE) | Start one stopped container |
| 🔽 **Scale down** (idle > TIMEOUT) | Stop highest-numbered excess container |
| 🔴 **At capacity** (running == MAX_TOTAL) | Cannot scale up |
| 🟡 **Minimum guaranteed** (running == MIN_IDLE) | Cannot scale down |

> ⚠️ The first `MIN_IDLE` containers (1..MIN_IDLE) form the **hot pool** — they are NEVER stopped and are always ready to record immediately.

### Why This Approach

The official Jitsi autoscaler requires Kubernetes or Google Cloud. This custom scaler:

- ✅ Runs entirely inside Docker — zero external dependencies
- ✅ Uses simple HTTP polling — no XMPP knowledge needed
- ✅ Starts/stops containers via Docker SDK — no orchestration required
- ✅ Configurable via environment variables — no code changes
- ✅ Lightweight — single Python file, minimal resource usage
- ✅ Predictable — deterministic logic, no ML/heuristics

---

## ☁️ ArvanCloud VOD Auto-Upload

```
  ┌─────────────────────────────────────────────────────┐
  │  Jibri finishes recording                           │
  │  → writes .mp4 + metadata.json to ./recordings/<id>/│
  └──────────────────────┬──────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────┐
  │  arvancloud-upload container (alpine)                │
  │  watches ./recordings/ every 60s                    │
  │  detects new .mp4 + metadata.json                   │
  └──────────────────────┬──────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │ tus protocol upload         │
          │                             │
          │ 1. POST /channels/{id}/files│
          │ 2. PATCH upload bytes       │
          │ 3. POST /channels/{id}/videos│
          └──────────────┬──────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────┐
  │  ArvanCloud VOD Platform                            │
  │  Video titled: "<room> YYYY/MM/DD HH:MM:SS"         │
  │  Auto-converted to HLS + MP4 (multi-res)            │
  └─────────────────────────────────────────────────────┘
```

### How It Works

After Jibri finishes recording, the `arvancloud-upload` container automatically:
1. Detects the completed recording (`.mp4` + `metadata.json`)
2. Extracts the room name from `metadata.json` and file modification time
3. Uploads the video to ArvanCloud VOD using the [tus resumable upload protocol](https://tus.io)
4. Creates a video entry in your configured channel with title `<room> YYYY/MM/DD HH:MM:SS`
5. Writes a state marker to `./state/uploaded/<uuid>` — never re-uploads

### Configuration

Add these to `.env`:

```bash
# ArvanCloud VOD auto-upload
ARVAN_API_KEY="apikey <your-api-key>"
ARVAN_CHANNEL_ID=<your-channel-id>
ARVAN_VOD_BASE_URL=https://napi.arvancloud.ir/vod/2.0
```

### Requirements

- An [ArvanCloud](https://arvancloud.ir) account with VOD service enabled
- A VOD channel created (you can create one via [API](https://napi.arvancloud.ir/vod/2.0/channels) or ArvanCloud panel)
- API key from ArvanCloud panel → Machine User → Create access key

### Files

| File | Description |
|------|-------------|
| `scripts/arvancloud-upload.sh` | Uploads one recording via tus protocol |
| `scripts/watch-recordings.sh` | Watcher loop (entrypoint of container) |
| `scripts/upload.Dockerfile` | Docker image (alpine + curl + jq + bash) |
| `docker-compose.yml` | `arvancloud-upload` service definition |
| `state/uploaded/` | Upload tracking markers |

### Manual Upload

```bash
# Upload a specific recording by session UUID
docker compose exec arvancloud-upload bash /usr/local/bin/arvancloud-upload.sh <session-uuid>

# Check upload logs
docker compose logs arvancloud-upload
```

---

<h3 dir="rtl" align="right">نحوه عملکرد اسکیلر خودکار</h3>

<p dir="rtl" align="right">
این یک اسکیلر خودکار (Auto-scaler) است که به صورت دستی با پایتون نوشته شده و وظیفه‌اش مدیریت خودکار کانتینرهای ضبط جیبری (Jibri) بر اساس نیاز واقعی است.
</p>

<h4 dir="rtl" align="right">نحوه کار:</h4>

<p dir="rtl" align="right">
<b>۱.</b> هر ۱۵ ثانیه یک بار از jicofo آمار می‌گیرد:<br>
&nbsp;&nbsp;&nbsp;&nbsp;- چند تا جیبری در دسترس (available) هستند<br>
&nbsp;&nbsp;&nbsp;&nbsp;- چند تا جیبری در مجموع (count) ثبت نام کرده‌اند
</p>

<p dir="rtl" align="right">
<b>۲.</b> تصمیم‌گیری بر اساس سه حالت:
</p>

<p dir="rtl" align="right">
<b>🔹 بوت اولیه:</b> اگر هیچ کانتینری در حال اجرا نباشد، به اندازه MIN_IDLE + 1 کانتینر شروع می‌کند.
</p>

<p dir="rtl" align="right">
<b>🔹 افزایش (Scale Up):</b> اگر جیبری‌های در دسترس از حد MIN_IDLE کمتر باشد و تعداد کل از MAX_TOTAL کمتر باشد، یک کانتینر متوقف شده را شروع می‌کند.
</p>

<p dir="rtl" align="right">
<b>🔹 کاهش (Scale Down):</b> اگر جیبری‌های در دسترس بیشتر از MIN_IDLE باشد و یک کانتینر اضافه برای بیش از IDLE_TIMEOUT (۵ دقیقه) بیکار مانده باشد، آن را متوقف می‌کند.
</p>

<h4 dir="rtl" align="right">ویژگی‌های مهم:</h4>

<p dir="rtl" align="right">
✅ کاملاً داخل داکر اجرا می‌شود — نیاز به سرویس خارجی ندارد<br>
✅ از HTTP ساده استفاده می‌کند — نیازی به XMPP نیست<br>
✅ کانتینرها را با Docker SDK شروع/متوقف می‌کند<br>
✅ از طریق متغیرهای محیطی (Environment Variables) قابل تنظیم است<br>
✅ بسیار سبک — یک فایل پایتون ساده<br>
✅ کانتینرهای ۱ تا MIN_IDLE هرگز متوقف نمی‌شوند (استخر آماده)
</p>

<h4 dir="rtl" align="right">متغیرهای قابل تنظیم:</h4>

<p dir="rtl" align="right">
<b>JICOFO_URL</b> — آدرس API جیکوفو<br>
<b>AUTOSCALER_POLL_INTERVAL</b> — فاصله بین هر بار چک کردن (ثانیه)<br>
<b>AUTOSCALER_MIN_IDLE</b> — حداقل جیبری بیکار آماده<br>
<b>AUTOSCALER_MAX_TOTAL</b> — حداکثر تعداد کل جیبری‌ها<br>
<b>AUTOSCALER_IDLE_TIMEOUT</b> — مهلت بیکاری قبل از توقف (ثانیه)<br>
<b>AUTOSCALER_CONTAINER_PREFIX</b> — پیشوند نام کانتینرها
</p>

---

## 🔄 Generating the Jibri Pool

The `generate-jibri-pool.sh` script reads `JIBRI_COUNT` from `.env` and generates `jibri-pool.yml`:

```bash
# Each instance gets:
#   - Container name:  jitsi-jibri-N
#   - Config volume:   $CONFIG/jibri-N
#   - Instance ID:     JIBRI_INSTANCE_ID=N
#   - Shared memory:   2GB
#   - Capability:      SYS_ADMIN

# To change pool size:
# 1. Edit .env:  JIBRI_COUNT=<new_number>
# 2. Run:        ./generate-jibri-pool.sh
```

---

## 🏗 Building Images

Use the `Makefile` to build Docker images:

| Command | Description |
|---|---|
| `make all` | Build all services locally |
| `make release` | Multi-arch buildx (amd64 + arm64) |
| `make build_<service>` | Build a single service |
| `make buildx_<service>` | Multi-arch build for one service |
| `make tag` | Tag an image |
| `make push` | Push an image to DockerHub |
| `make clean` | Stop and remove all containers |
| `make prepare` | Force rebuild all (no cache) |

**Buildable services:** `base`, `base-java`, `web`, `prosody`, `jicofo`, `jvb`, `jigasi`, `jibri`

---

## 📁 Directory Structure

```
services/
├── 📄 .env                        # Main configuration
├── 📄 .env.jibri                  # Jibri per-container environment
├── 📄 docker-compose.yml          # Main compose file
├── 📄 jibri-pool.yml              # Auto-generated jibri instances
├── 📄 generate-jibri-pool.sh      # Pool regeneration script
├── 📄 setup.sh                    # Interactive setup script
├── 📄 Makefile                    # Build automation
│
├── 📁 jibri-autoscaler/           # Custom auto-scaler (Python)
│   ├── 📄 Dockerfile
│   └── 📄 main.py                 # Scaling logic (206 lines)
│
├── 📁 config/                     # Runtime configuration
│   ├── 📁 jibri-{1..N}/           # Per-instance config + logs
│   ├── 📁 jicofo/
│   ├── 📁 jvb/
│   ├── 📁 prosody/
│   └── 📁 web/
│
├── 📁 jibri/                      # Jibri Docker image source
├── 📁 jicofo/                     # Jicofo Docker image source
├── 📁 jvb/                        # JVB Docker image source
├── 📁 prosody/                    # Prosody Docker image source
├── 📁 web/                        # Web Docker image source
├── 📁 base/                       # Base Docker image
├── 📁 base-java/                  # Java base Docker image
│
├── 📁 grafana/                    # Grafana provisioning
├── 📁 prometheus/                 # Prometheus config
├── 📁 log-analyser/               # Loki + OTEL config
├── 📁 scripts/                    # Utility scripts
│   ├── 📄 arvancloud-upload.sh    # ArvanCloud VOD upload
│   ├── 📄 watch-recordings.sh     # Recording watcher daemon
│   └── 📄 upload.Dockerfile       # Dockerfile for upload container
├── 📁 state/                      # Runtime state
│   └── 📁 uploaded/               # Upload tracking markers
├── 📁 rtcstats/                   # WebRTC stats
│
├── 📁 recordings/                 # Recordings storage
├── 📁 resources/                  # Images and icons
└── 📁 examples/                   # Example configs
```

---

## 🔧 Troubleshooting

| 🚨 Problem | ✅ Solution |
|---|---|
| **Jibri containers crash** | Ensure `shm_size: 2gb` and `SYS_ADMIN` capability. Check: `docker compose logs jibri-1` |
| **Autoscaler not scaling** | Ensure `JICOFO_ENABLE_REST=1`. Check: `docker compose logs jibri-autoscaler` |
| **Can't connect to Jitsi** | Open ports 8000/tcp, 8443/tcp, 10000/udp. Verify `PUBLIC_URL` |
| **Recording not working** | Check `.env.jibri` credentials. Verify jibri can reach prosody |

---

## 💻 Useful Commands

```bash
# View all running services
docker compose -f docker-compose.yml -f jibri-pool.yml ps

# Watch autoscaler logs in real-time
docker compose logs -f jibri-autoscaler

# Check jibri instance logs
docker compose logs -f jibri-1

# Restart the autoscaler
docker compose up -d --force-recreate jibri-autoscaler

# Resize the jibri pool
#   vi .env   →  change JIBRI_COUNT
#   ./generate-jibri-pool.sh

# Stop everything
docker compose -f docker-compose.yml -f jibri-pool.yml down

# Check jicofo stats
curl http://localhost:8888/stats
```

---

## 📄 License

**Apache License 2.0** — See [`LICENSE`](LICENSE) for full details.

<p align="center">
  <sub>Built with ❤️ using</sub>
  <br>
  <a href="https://jitsi.org/">Jitsi Meet</a> ·
  <a href="https://docker.com">Docker</a> ·
  <a href="https://python.org">Python</a>
</p>
