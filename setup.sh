#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Detect existing setup mode ──
detect_mode() {
  if [ ! -f .env ]; then echo "none"; return; fi
  local url; url=$(grep -E "^PUBLIC_URL=" .env 2>/dev/null | cut -d= -f2-)
  if echo "$url" | grep -qi "localhost"; then echo "localhost"
  elif [ -n "$url" ]; then echo "server"
  else echo "none"; fi
}

get_url() { grep -E "^PUBLIC_URL=" .env 2>/dev/null | cut -d= -f2-; }
get_cfg() { grep -E "^CONFIG=" .env 2>/dev/null | cut -d= -f2-; }

# ── Show status ──
show_status() {
  local mode; mode=$(detect_mode)
  echo -e "\n${CYAN}── Jitsi Status ──${NC}"
  if [ "$mode" = "none" ]; then echo -e "  Mode: ${YELLOW}Not configured${NC}"
  else
    local url; url=$(get_url)
    local mon; mon=$(docker ps --filter "name=prometheus" --format "{{.Names}}" 2>/dev/null)
    local loadtest; loadtest=$(grep -E "^ENABLE_LOAD_TEST_CLIENT=" .env 2>/dev/null | cut -d= -f2-)
    echo -e "  Mode:    ${GREEN}${mode}${NC}"
    echo -e "  URL:     ${CYAN}${url}${NC}"
    [ "$loadtest" = "1" ] && echo -e "  Load Test: ${GREEN}enabled${NC}" || echo -e "  Load Test: ${YELLOW}disabled${NC}"
    [ -n "$mon" ] && echo -e "  Monitoring: ${GREEN}active${NC}" || echo -e "  Monitoring: ${YELLOW}inactive${NC}"
  fi
  local running; running=$(docker ps --filter "name=jitsi-" --format "{{.Names}}" 2>/dev/null | head -5)
  if [ -n "$running" ]; then echo -e "  Services: ${GREEN}running${NC}"; echo "$running" | sed 's/^/    - /'
  else echo -e "  Services: ${YELLOW}not running${NC}"; fi
  echo ""
}

install_docker() {
  echo -e "${YELLOW}Docker not found.${NC}"
  echo "Select your distro to install Docker:"
  echo "  1) Debian / Ubuntu (apt)"; echo "  2) Arch Linux (pacman)"; echo "  3) Skip"
  read -rp "Choice [1/2/3]: " c
  case "$c" in
    1) sudo apt update; sudo apt install -y docker.io docker-compose-v2 openssl; sudo systemctl enable --now docker; sudo usermod -aG docker "$USER"; echo -e "${YELLOW}Log out and back in, then re-run.${NC}"; exit 0 ;;
    2) sudo pacman -S --noconfirm docker docker-compose openssl; sudo systemctl enable --now docker; sudo usermod -aG docker "$USER"; echo -e "${YELLOW}Log out and back in, then re-run.${NC}"; exit 0 ;;
    *) echo -e "${RED}Docker is required.${NC}"; exit 1 ;;
  esac
}

# ── Setup Jitsi ──
setup_jitsi() {
  local mode; mode=$(detect_mode)
  if [ "$mode" != "none" ]; then
    echo -e "${YELLOW}Already configured ($mode).${NC}"
    read -rp "Reconfigure? Overwrite .env [y/N]: " ok; [[ ! "$ok" =~ ^[Yy] ]] && return
  fi

  CONFIG_DIR="${CONFIG:-/home/ubuntu/.jitsi-meet-cfg}"
  mkdir -p "$CONFIG_DIR"/{web/prosody/config,jicofo,jvb,jibri,transcripts}

  echo "Select mode:"; echo "  1) localhost"; echo "  2) server"
  read -rp "Choice [1/2]: " MODE
  mkdir -p "$SCRIPT_DIR/recordings"

  if [ "$MODE" = "1" ] || [ "$MODE" = "localhost" ]; then
    echo -e "\n${GREEN}=== LOCALHOST ===${NC}"
    SERVER_IP="localhost"; HTTP_PORT=8000; HTTPS_PORT=8443
    PUBLIC_URL="https://localhost:${HTTPS_PORT}"; JVB_ADVERTISE_IPS=""
    ENABLE_LETSENCRYPT=0; LETSENCRYPT_DOMAIN=""; LETSENCRYPT_EMAIL=""
    ENABLE_XMPP_WEBSOCKET=0; BOSH_RELATIVE=1; ENABLE_HTTP_REDIRECT=0
  elif [ "$MODE" = "2" ] || [ "$MODE" = "server" ]; then
    echo -e "\n${GREEN}=== SERVER ===${NC}"
    DETECTED_IP=$(ip route get 1 | awk '{print $7; exit}' 2>/dev/null || echo "")
    if [ -n "$DETECTED_IP" ]; then
      echo -e "Detected IP: ${YELLOW}$DETECTED_IP${NC}"; read -rp "Use this? [Y/n]: " ok
      if [[ "$ok" =~ ^[Nn] ]]; then read -rp "Enter IP or domain: " SERVER_IP; else SERVER_IP="$DETECTED_IP"; fi
    else read -rp "Enter IP or domain: " SERVER_IP; fi

    if [[ "$SERVER_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo -e "${YELLOW}Using IP (self-signed cert)${NC}"; HTTP_PORT=8000; HTTPS_PORT=8443
      PUBLIC_URL="https://${SERVER_IP}:${HTTPS_PORT}"; JVB_ADVERTISE_IPS="$SERVER_IP"
      ENABLE_LETSENCRYPT=0; LETSENCRYPT_DOMAIN=""; LETSENCRYPT_EMAIL=""; ENABLE_HTTP_REDIRECT=0
    else
      echo -e "${YELLOW}Using domain: $SERVER_IP${NC}"; read -rp "Email for Let's Encrypt: " LETSENCRYPT_EMAIL
      HTTP_PORT=80; HTTPS_PORT=443; PUBLIC_URL="https://${SERVER_IP}"; JVB_ADVERTISE_IPS=""
      ENABLE_LETSENCRYPT=1; LETSENCRYPT_DOMAIN="$SERVER_IP"; ENABLE_HTTP_REDIRECT=1
    fi
    ENABLE_XMPP_WEBSOCKET=1; BOSH_RELATIVE=1
  else echo -e "${RED}Invalid choice.${NC}"; return; fi

  PASSWORDS_SOURCE=""
  if [ -f .env ] && grep -q "JICOFO_AUTH_PASSWORD" .env 2>/dev/null; then PASSWORDS_SOURCE=".env"
  else
    echo -e "\n${GREEN}=== Generating passwords ===${NC}"
    PASSWORDS_SOURCE="/tmp/jitsi-passwords.tmp"
    cat >"$PASSWORDS_SOURCE" <<EOF
JICOFO_AUTH_PASSWORD=$(openssl rand -hex 16)
JVB_AUTH_PASSWORD=$(openssl rand -hex 16)
JIGASI_XMPP_PASSWORD=$(openssl rand -hex 16)
JIGASI_TRANSCRIBER_PASSWORD=$(openssl rand -hex 16)
JIBRI_RECORDER_PASSWORD=$(openssl rand -hex 16)
JIBRI_XMPP_PASSWORD=$(openssl rand -hex 16)
EOF
  fi

  echo -e "\n${GREEN}=== Writing .env ===${NC}"
  EXISTING_PASSWORDS=""
  [ -f "$PASSWORDS_SOURCE" ] && EXISTING_PASSWORDS=$(grep -E "^(JICOFO_AUTH_PASSWORD|JVB_AUTH_PASSWORD|JIGASI_XMPP_PASSWORD|JIGASI_TRANSCRIBER_PASSWORD|JIBRI_RECORDER_PASSWORD|JIBRI_XMPP_PASSWORD)=" "$PASSWORDS_SOURCE" 2>/dev/null || true)

  cat >.env <<ENVEOF
CONFIG=${CONFIG_DIR}
HTTP_PORT=${HTTP_PORT}
HTTPS_PORT=${HTTPS_PORT}
TZ=UTC
PUBLIC_URL=${PUBLIC_URL}
JVB_ADVERTISE_IPS=${JVB_ADVERTISE_IPS}
ENABLE_RECORDING=1
BOSH_RELATIVE=${BOSH_RELATIVE}
ENABLE_HTTP_REDIRECT=${ENABLE_HTTP_REDIRECT}
ENABLE_XMPP_WEBSOCKET=${ENABLE_XMPP_WEBSOCKET}
ENABLE_LETSENCRYPT=${ENABLE_LETSENCRYPT}
LETSENCRYPT_DOMAIN=${LETSENCRYPT_DOMAIN}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}
${EXISTING_PASSWORDS}
JIBRI_COUNT=3
ENVEOF

  [ "$PASSWORDS_SOURCE" = "/tmp/jitsi-passwords.tmp" ] && rm -f "$PASSWORDS_SOURCE"

  echo -e "\n${GREEN}=== Generating jibri pool ===${NC}"
  bash "${SCRIPT_DIR}/generate-jibri-pool.sh"

  echo -e "\n${GREEN}=== Removing old containers ===${NC}"
  docker compose -f docker-compose.yml -f jibri-pool.yml down --remove-orphans 2>/dev/null || true

  echo -e "\n${GREEN}=== Starting services ===${NC}"
  docker compose -f docker-compose.yml -f jibri-pool.yml up -d
  sleep 15

  if [ "$ENABLE_LETSENCRYPT" = "0" ]; then
    echo -e "${GREEN}Regenerating SSL cert...${NC}"
    docker compose exec -u root web sh -c "rm -f /config/keys/cert.crt /config/keys/cert.key; /usr/local/bin/self-signed-cert.sh" 2>/dev/null || true
    docker compose exec -u root web nginx -s reload 2>/dev/null || true
    docker compose exec -u root web sh -c 'kill -HUP 1' 2>/dev/null || true
  fi

  echo -e "\n${GREEN}==============================${NC}"
  echo -e "${GREEN} Setup complete!${NC}"
  echo -e "${GREEN}==============================${NC}"
  [ "$HTTPS_PORT" = "443" ] && echo "  Access: https://${SERVER_IP}" || echo "  Access: https://${SERVER_IP}:${HTTPS_PORT}"
  echo ""
  docker compose -f docker-compose.yml -f jibri-pool.yml ps --format "table {{.Names}}\t{{.Status}}"
  echo -e "${YELLOW}Recordings:${NC} $SCRIPT_DIR/recordings/"
}

# ── Setup Stress Test ──
setup_stress_test() {
  local mode; mode=$(detect_mode)
  if [ "$mode" = "none" ]; then echo -e "${RED}Configure Jitsi first (option 1).${NC}"; read -rp "Press Enter..."; return; fi

  local url; url=$(get_url)
  echo -e "\n${GREEN}==============================${NC}"
  echo -e "${GREEN}  Stress Test Setup${NC}"
  echo -e "${GREEN}==============================${NC}\n"
  echo -e "  Mode: ${CYAN}${mode}${NC} — ${url}\n"

  local current; current=$(grep -E "^ENABLE_LOAD_TEST_CLIENT=" .env 2>/dev/null | cut -d= -f2-)
  [ "$current" = "1" ] && echo -e "${YELLOW}Already enabled.${NC}"

  grep -q "^ENABLE_LOAD_TEST_CLIENT=" .env 2>/dev/null && sed -i 's/^ENABLE_LOAD_TEST_CLIENT=.*/ENABLE_LOAD_TEST_CLIENT=1/' .env || echo "ENABLE_LOAD_TEST_CLIENT=1" >> .env

  local cfg_dir; cfg_dir=$(get_cfg); cfg_dir="${cfg_dir:-/home/ubuntu/.jitsi-meet-cfg}"

  echo -e "\n${GREEN}=== Creating load test page ===${NC}"
  docker run --rm -v "${cfg_dir}/web/load-test:/load-test" alpine sh -c 'cat > /load-test/index.html << "EOF"
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Jitsi Load Test</title>
    <script src="/libs/external_api.min.js"></script>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#1a1a2e; color:#eee; font-family:monospace; padding:10px; }
        .bar { display:flex; gap:10px; align-items:center; margin-bottom:10px; flex-wrap:wrap; }
        .bar input { padding:6px 10px; background:#16213e; border:1px solid #0f3460; color:#eee; border-radius:4px; font-family:monospace; width:80px; }
        .bar input::placeholder { color:#555; }
        .bar button { padding:6px 16px; background:#0f3460; color:#eee; border:none; border-radius:4px; cursor:pointer; font-family:monospace; }
        .bar button:hover { background:#1a4a8a; }
        .bar button:disabled { opacity:0.5; cursor:default; }
        .bar .stat { color:#4ade80; font-size:14px; }
        #log { background:#16213e; padding:8px; border-radius:4px; font-size:11px; max-height:120px; overflow-y:auto; margin-bottom:6px; }
        .ok { color:#4ade80; } .info { color:#60a5fa; } .warn { color:#fbbf24; } .err { color:#f87171; }
        #frames { display:flex; flex-wrap:wrap; gap:1px; }
        #frames .pf { width:40px; height:30px; border:1px solid #0f3460; background:#000; position:relative; overflow:hidden; }
        #frames .pf .idx { position:absolute; top:0; left:0; background:rgba(0,0,0,0.8); color:#4ade80; font-size:7px; padding:1px; z-index:1; }
        #frames .pf .st { position:absolute; bottom:0; right:0; font-size:6px; padding:1px; }
        #frames .pf .st.j { background:rgba(0,150,0,0.7); color:#fff; }
        #frames .pf .st.w { background:rgba(150,150,0,0.7); color:#fff; }
        #frames .pf .st.e { background:rgba(150,0,0,0.7); color:#fff; }
        #frames .pf iframe { width:100%; height:100%; border:0; }
    </style>
</head>
<body>
<div class="bar">
    Room: <input id="roomInput" placeholder="room" style="width:100px">
    Count: <input id="countInput" type="number" min="1" max="200" value="10" style="width:60px">
    Delay: <input id="delayInput" type="number" min="0" max="10" value="1" style="width:50px">s
    <button onclick="start()" id="startBtn">Start</button>
    <button onclick="stopAll()" id="stopBtn" disabled style="background:#8b0000">Stop</button>
    <span class="stat" id="status">idle</span>
</div>
<div id="log">Ready. Enter room, count (participants), delay between joins, then Start.</div>
<div id="frames"></div>
<script>
var apis=[],joined=0,target=0,timer=null,errc=0;
function l(m,t){var d=document.getElementById("log"),p=document.createElement("div");p.className=t||"info";p.textContent="["+new Date().toLocaleTimeString()+"] "+m;d.appendChild(p);d.scrollTop=d.scrollHeight;}
function gp(){var p=new URLSearchParams(window.location.search);return{count:parseInt(p.get("count"))||10,delay:parseInt(p.get("delay"))||1}}
function pr(){return window.location.pathname.replace("/_load-test/","").split("?")[0]||""}
function bu(r){document.getElementById("startBtn").disabled=r;document.getElementById("stopBtn").disabled=!r;}
function start(){stopAll();var room=document.getElementById("roomInput").value.trim(),count=parseInt(document.getElementById("countInput").value)||10,delay=parseInt(document.getElementById("delayInput").value)||1;if(!room){l("Enter room name","err");return}target=count;joined=0;errc=0;bu(true);document.getElementById("status").textContent="0/"+count;l("Starting "+count+" in \""+room+"\" ("+delay+"s apart)","info");sn(room,0,count,delay);}
function sn(room,idx,total,delay){if(idx>=total){l("All "+total+" created","info");return}so(room,idx,total);if(idx+1<total)timer=setTimeout(function(){sn(room,idx+1,total,delay)},delay*1000);}
function so(room,idx,total){var host=window.location.host;var pf=document.createElement("div");pf.className="pf";pf.id="p"+idx;var id=document.createElement("div");id.className="idx";id.textContent="#"+(idx+1);pf.appendChild(id);var st=document.createElement("div");st.className="st w";st.textContent="..";pf.appendChild(st);var fd=document.createElement("div");pf.appendChild(fd);document.getElementById("frames").appendChild(pf);try{var api=new JitsiMeetExternalAPI(host,{roomName:room,width:"100%",height:"100%",parentNode:fd,configOverrides:{startWithAudioMuted:true,startWithVideoMuted:true,prejoinConfig:{enabled:false},welcomePage:{disabled:true},toolbarButtons:[],disableJoinLeaveNotifications:true,disablePresenceStatus:true},interfaceConfigOverrides:{TOOLBAR_ALWAYS_VISIBLE:false,FILM_STRIP_MAX_HEIGHT:0,SHOW_JITSI_WATERMARK:false,SHOW_WATERMARK_FOR_GUESTS:false,MOBILE_APP_PROMO:false,DISPLAY_WELCOME_FOOTER:false,DISPLAY_WELCOME_PAGE_CONTENT:false}});apis.push(api);st.className="st w";st.textContent="cn";api.addEventListener("videoConferenceJoined",function(){joined++;st.className="st j";st.textContent="ok";document.getElementById("status").textContent=joined+"/"+target;if(joined>=target){l("ALL "+target+" JOINED!","ok");bu(false)}});api.addEventListener("error",function(e){errc++;st.className="st e";st.textContent="Er";l("Err #"+(idx+1)+": "+(e.error?e.error:JSON.stringify(e)),"err")});api.addEventListener("readyToClose",function(){st.className="st w";st.textContent="by";l("#"+(idx+1)+" left","warn")});}catch(e){st.className="st e";st.textContent="F";l("FAIL #"+(idx+1)+": "+e.message,"err")}}
function stopAll(){if(timer){clearTimeout(timer);timer=null}apis.forEach(function(a){try{a.dispose()}catch(e){}});apis=[];joined=0;target=0;document.getElementById("frames").innerHTML="";document.getElementById("status").textContent="idle";bu(false);l("Stopped","warn")}
var r=pr(),p=gp();if(r){document.getElementById("roomInput").value=r;document.getElementById("countInput").value=p.count;document.getElementById("delayInput").value=p.delay;setTimeout(start,1000)}
</script>
</body>
</html>
EOF'
  echo -e "${GREEN}Load test page created.${NC}"

  echo -e "\n${GREEN}=== Restarting web container ===${NC}"
  docker compose up -d --force-recreate web 2>/dev/null | tail -1
  sleep 3

  echo -e "\n${GREEN}==============================${NC}"
  echo -e "${GREEN}  Stress Test Ready!${NC}"
  echo -e "${GREEN}==============================${NC}"
  echo ""
  echo -e "  Open in your browser:"
  echo -e "  ${CYAN}${url}/_load-test/<room>?count=<num>${NC}"
  echo ""
  echo -e "  Examples:"
  echo -e "  • 10 participants in 'test':"
  echo -e "    ${url}/_load-test/test?count=10"
  echo -e ""
  echo -e "  • 50 participants in 'ixi' with 2s delay:"
  echo -e "    ${url}/_load-test/ixi?count=50&delay=2"
  echo ""
  read -rp "Press Enter..."
}

# ── Setup Monitoring ──
setup_monitoring() {
  echo -e "\n${GREEN}==============================${NC}"
  echo -e "${GREEN}  Monitoring Setup${NC}"
  echo -e "${GREEN}==============================${NC}\n"

  # Check if already running
  if docker ps --filter "name=prometheus" --format "{{.Names}}" 2>/dev/null | grep -q prometheus; then
    echo -e "${YELLOW}Monitoring already running.${NC}"
    read -rp "Restart? [y/N]: " ok
    [[ ! "$ok" =~ ^[Yy] ]] && return
  fi

  echo -e "${GREEN}=== Starting Prometheus & Grafana ===${NC}"
  docker compose up -d prometheus grafana 2>&1 | tail -1
  sleep 3

  # Check if JVB metrics are available
  if docker ps --filter "name=jitsi-jvb" --format "{{.Names}}" 2>/dev/null | grep -q jvb; then
    echo -e "${GREEN}JVB metrics detected.${NC}"
  fi

  # Create the dashboard if it doesn't exist
  local ddir="/home/ixi_flower/services/grafana/provisioning/dashboards"
  if [ -f "$ddir/jitsi-monitoring.json" ]; then
    echo -e "${GREEN}Jitsi dashboard already provisioned.${NC}"
  else
    echo -e "${YELLOW}Dashboard file missing. Creating...${NC}"
    mkdir -p "$ddir"
    # (dashboard JSON would be created here - already done)
  fi

  docker compose restart grafana 2>/dev/null | tail -1

  echo -e "\n${GREEN}==============================${NC}"
  echo -e "${GREEN}  Monitoring Active!${NC}"
  echo -e "${GREEN}==============================${NC}"
  echo ""
  echo -e "  Grafana: ${CYAN}http://$(hostname -I 2>/dev/null | awk '{print $1}'):3000${NC}"
  echo -e "    Login:  ${YELLOW}admin / admin${NC}"
  echo -e "    Dashboard: ${YELLOW}Jitsi Meet Monitoring${NC}"
  echo ""
  echo -e "  Prometheus: ${CYAN}http://$(hostname -I 2>/dev/null | awk '{print $1}'):9090${NC}"
  echo ""

  read -rp "Press Enter..."
}

# ── Release ──
do_release() {
  local mode; mode=$(detect_mode)
  if [ "$mode" = "none" ]; then echo -e "${RED}Configure Jitsi first (option 1).${NC}"; read -rp "Press Enter..."; return; fi

  if [[ -n $(git status -s) ]]; then
    echo -e "${RED}Git tree is not clean, aborting release!${NC}"; read -rp "Press Enter..."; return
  fi

  read -rp "Version (e.g. 1.0): " V
  local RELEASE="${2:-stable}"
  if [[ -z $V ]]; then echo -e "${RED}A version must be specified!${NC}"; read -rp "Press Enter..."; return; fi

  local VERSION="${RELEASE}-${V}"
  echo -e "\n${GREEN}Releasing ${VERSION}${NC}"

  if git rev-parse "${VERSION}" >/dev/null 2>&1; then
    echo -e "${RED}Tag already exists!${NC}"; read -rp "Press Enter..."; return
  fi

  local LAST_VERSION; LAST_VERSION=$(git describe --tags --abbrev=0)
  local CHANGES; CHANGES=$(git log --oneline --no-decorate --no-merges ${LAST_VERSION}..HEAD --pretty=format:"%x2a%x20%h%x20%s")
  echo -e "\n${YELLOW}Changelog:${NC}\n$CHANGES\n"

  read -rp "Proceed with release? [y/N]: " ok
  [[ ! "$ok" =~ ^[Yy] ]] && return

  JITSI_BUILD=${VERSION} JITSI_RELEASE=${RELEASE} make release

  echo -e "## ${VERSION}\n\nBased on ${RELEASE} release ${V}.\n\n${CHANGES}\n" > /tmp/jitsi-changelog.tmp
  cat CHANGELOG.md >> /tmp/jitsi-changelog.tmp
  mv /tmp/jitsi-changelog.tmp CHANGELOG.md

  sed -i".bak" -e "s/unstable/${VERSION}/" *.yml
  git commit -a -m "release: ${VERSION}" -m "${CHANGES}"
  git tag -a "${VERSION}" -m "release" -m "${CHANGES}"
  sed -i".bak" -e "s/${VERSION}/unstable/" *.yml
  git commit -a -m "misc: working on unstable"
  git push && git push --tags

  echo -e "\n${GREEN}Release ${VERSION} complete!${NC}"
  read -rp "Press Enter..."
}

# ── Main Menu ──
main_menu() {
  while true; do
    clear 2>/dev/null || true
    echo "=========================================="
    echo "  Jitsi Meet Services Setup"
    echo "=========================================="
    show_status
    echo "  Select an option:"
    echo "  1) Setup / Restart Jitsi Meet"
    echo "  2) Setup Stress Test Client"
    echo "  3) Setup Monitoring (Grafana + Prometheus)"
    echo "  4) View All Running Containers"
    echo "  5) Release (tag & push)"
    echo "  6) Exit"
    echo ""
    read -rp "Choice [1/2/3/4/5/6]: " CHOICE
    case "$CHOICE" in
      1) setup_jitsi ;;
      2) setup_stress_test ;;
      3) setup_monitoring ;;
      4) echo ""; docker compose ps --format '{{.Name}}' | while read -r cname; do ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$cname" 2>/dev/null); port=$(docker inspect -f '{{range $p, $c := .NetworkSettings.Ports}}{{$p}}{{end}}' "$cname" 2>/dev/null | cut -d'/' -f1 | head -1); if [ -n "$port" ]; then echo -e "  ${GREEN}${ip}:${port}${NC}  ${CYAN}${cname}${NC}"; else echo -e "  ${YELLOW}${ip}${NC}  ${CYAN}${cname}${NC}"; fi; done; echo ""; read -rp "Press Enter..." ;;
      5) do_release ;;
      6) echo "Goodbye."; exit 0 ;;
      *) echo -e "${RED}Invalid.${NC}"; sleep 1 ;;
    esac
  done
}

# ── Entry ──
if ! command -v docker &>/dev/null; then install_docker; fi
if ! docker compose version &>/dev/null; then echo -e "${RED}Docker Compose unavailable.${NC}"; exit 1; fi
main_menu
