1|1|#!/bin/bash
2|2|# arvancloud-upload.sh <session-uuid>
3|3|# Uploads a Jibri recording directory to ArvanCloud VOD
4|4|# and generates a SECURE player URL (IP-locked + time-expiring).
5|5|#
6|6|# Uses: ARVAN_API_KEY, ARVAN_CHANNEL_ID, ARVAN_SECURE_LINK_KEY from environment
7|7|#
8|8|# Output files (per recording):
9|9|#   /state/uploaded/<uuid>          — upload timestamp marker
10|10|#   /state/players/<uuid>.url       — secure player URL (for embedding)
11|11|#   /state/players/<uuid>.json      — full metadata + secure URLs
12|12|
13|13|set -euo pipefail
14|14|
15|15|UUID="${1:-}"
16|16|RECORDINGS_DIR="${RECORDINGS_DIR:-/recordings}"
17|17|STATE_DIR="${STATE_DIR:-/state}"
18|18|PLAYER_DIR="${STATE_DIR}/players"
19|19|
20|20|[ -z "$UUID" ] && echo "Usage: $0 <session-uuid>" && exit 1
21|21|
22|22|SESSION_DIR="$RECORDINGS_DIR/$UUID"
23|23|METADATA="$SESSION_DIR/metadata.json"
24|24|MARKER="$STATE_DIR/$UUID"
25|25|PLAYER_URL_FILE="$PLAYER_DIR/$UUID.url"
26|26|PLAYER_JSON_FILE="$PLAYER_DIR/$UUID.json"
27|27|
28|28|mkdir -p "$PLAYER_DIR"
29|29|
30|30|# ── Skip if already uploaded ──────────────────────────────────
31|31|if [ -f "$MARKER" ]; then
32|32|  exit 0
33|33|fi
34|34|
35|35|# ── Find the mp4 ──────────────────────────────────────────────
36|36|shopt -s nullglob
37|37|MP4_FILES=("$SESSION_DIR"/*.mp4)
38|38|shopt -u nullglob
39|39|MP4_FILE="${MP4_FILES[0]:-}"
40|40|
41|41|if [ ! -f "$METADATA" ] || [ -z "$MP4_FILE" ]; then
42|42|  exit 1
43|43|fi
44|44|
45|45|# ── Config ────────────────────────────────────────────────────
AUTH="Authorization: ${ARVAN_API_KEY}"
47|47|BASE="${ARVAN_VOD_BASE_URL:-https://napi.arvancloud.ir/vod/2.0}"
48|48|CHANNEL_ID="${ARVAN_CHANNEL_ID}"
49|49|SECURE_KEY="${ARVAN_SECURE_LINK_KEY:-}"
50|50|
51|51|if [ -z "${ARVAN_API_KEY:-}" ] || [ -z "$CHANNEL_ID" ]; then
52|52|  echo "[FAIL] $UUID — ARVAN_API_KEY or ARVAN_CHANNEL_ID not set"
53|53|  exit 1
54|54|fi
55|55|
56|56|# ── Extract metadata ──────────────────────────────────────────
57|57|ROOM=$(jq -r '.meeting_url // empty' "$METADATA" | sed 's|.*/||')
58|58|TIMESTAMP=$(date -d "@$(stat -c %Y "$MP4_FILE")" '+%Y/%m/%d %H:%M:%S' 2>/dev/null || date '+%Y/%m/%d %H:%M:%S')
59|59|[ -z "$ROOM" ] && ROOM="unknown"
60|60|TITLE="$ROOM $TIMESTAMP"
61|61|
62|62|FILESIZE=$(stat -c %s "$MP4_FILE")
63|63|FILENAME=$(basename "$MP4_FILE")
64|64|FILENAME_B64=$(echo -n "$FILENAME" | base64 -w0)
65|65|FILETYPE_B64=$(echo -n "video/mp4" | base64 -w0)
66|66|
67|67|echo "[UPLOAD] $UUID → $TITLE ($FILESIZE bytes)"
68|68|
69|69|# ═══════════════════════════════════════════════════════════════
70|70|# STEP 1: Initiate tus upload
71|71|# ═══════════════════════════════════════════════════════════════
72|72|LOCATION=$(curl -s -D - \
73|73|  -X POST "$BASE/channels/$CHANNEL_ID/files" \
74|74|  -H "$AUTH" \
75|75|  -H "tus-resumable: 1.0.0" \
76|76|  -H "upload-length: $FILESIZE" \
77|77|  -H "upload-metadata: filename $FILENAME_B64,filetype $FILETYPE_B64" \
78|78|  2>/dev/null | grep -i "^location:" | awk '{print $2}' | tr -d '\r\n')
79|79|
80|80|if [ -z "$LOCATION" ]; then
81|81|  echo "[FAIL] $UUID — tus initiation failed"
82|82|  exit 1
83|83|fi
84|84|
85|85|FILE_ID=$(echo "$LOCATION" | awk -F/ '{print $NF}')
86|86|
87|87|# ═══════════════════════════════════════════════════════════════
88|88|# STEP 2: Upload file bytes (tus PATCH)
89|89|# ═══════════════════════════════════════════════════════════════
90|90|HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
91|91|  -X PATCH "$LOCATION" \
92|92|  -H "$AUTH" \
93|93|  -H "tus-resumable: 1.0.0" \
94|94|  -H "upload-offset: 0" \
95|95|  -H "Content-Type: application/offset+octet-stream" \
96|96|  --data-binary "@$MP4_FILE" \
97|97|  2>/dev/null)
98|98|
99|99|if [ "$HTTP_CODE" != "204" ]; then
100|100|  echo "[FAIL] $UUID — tus upload failed (HTTP $HTTP_CODE)"
101|101|  exit 1
102|102|fi
103|103|
104|104|# ═══════════════════════════════════════════════════════════════
105|105|# STEP 3: Create video entry
106|106|# ═══════════════════════════════════════════════════════════════
107|107|VIDEO_RESPONSE=$(curl -s \
108|108|  -X POST "$BASE/channels/$CHANNEL_ID/videos" \
109|109|  -H "Content-Type: application/json" \
110|110|  -H "$AUTH" \
111|111|  -d "{\"title\":\"$TITLE\",\"file_id\":\"$FILE_ID\",\"convert_mode\":\"auto\"}" \
112|112|  2>/dev/null)
113|113|
114|114|VIDEO_ID=$(echo "$VIDEO_RESPONSE" | jq -r '.data.id // empty')
115|115|
116|116|if [ -z "$VIDEO_ID" ]; then
117|117|  echo "[FAIL] $UUID — video creation failed"
118|118|  echo "$VIDEO_RESPONSE"
119|119|  exit 1
120|120|fi
121|121|
122|122|echo "[VIDEO] $UUID — created as $VIDEO_ID"
123|123|
124|124|# ═══════════════════════════════════════════════════════════════
125|125|# STEP 4: Wait for video processing to complete
126|126|# ═══════════════════════════════════════════════════════════════
127|127|MAX_WAIT=300  # 5 minutes max
128|128|WAIT_INTERVAL=10
129|129|ELAPSED=0
130|130|
131|131|echo "[PROCESS] $UUID — waiting for conversion..."
132|132|while [ $ELAPSED -lt $MAX_WAIT ]; do
133|133|  STATUS=$(curl -s "$BASE/videos/$VIDEO_ID" \
134|134|    -H "$AUTH" \
135|135|    -H "Accept: application/json" \
136|136|    2>/dev/null | jq -r '.data.status // "unknown"')
137|137|
138|138|  case "$STATUS" in
139|139|    ready)
140|140|      echo "[PROCESS] $UUID — ready (${ELAPSED}s)"
141|141|      break
142|142|      ;;
143|143|    converting_fail|error)
144|144|      echo "[FAIL] $UUID — conversion failed (status: $STATUS)"
145|145|      exit 1
146|146|      ;;
147|147|    *)
148|148|      sleep "$WAIT_INTERVAL"
149|149|      ELAPSED=$((ELAPSED + WAIT_INTERVAL))
150|150|      ;;
151|151|  esac
152|152|done
153|153|
154|154|if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
155|155|  echo "[WARN] $UUID — conversion timeout after ${MAX_WAIT}s, continuing anyway"
156|156|fi
157|157|
158|158|# ═══════════════════════════════════════════════════════════════
159|159|# STEP 5: Generate SECURE player URL (IP-locked, 7-day expiry)
160|160|# ═══════════════════════════════════════════════════════════════
161|161|if [ -n "$SECURE_KEY" ]; then
162|162|  # Default: 7-day expiry, no IP lock (IP will be set at embed time)
163|163|  SECURE_EXPIRE=$(($(date +%s) + 604800))  # 7 days
164|164|  SECURE_IP="${SECURE_IP:-}"  # leave empty = CDN uses requester IP
165|165|
166|166|  SECURE_PARAMS="secure_expire_time=$SECURE_EXPIRE"
167|167|  [ -n "$SECURE_IP" ] && SECURE_PARAMS="$SECURE_PARAMS&secure_ip=$SECURE_IP"
168|168|
169|169|  VIDEO_DATA=$(curl -s \
170|170|    -X GET "$BASE/videos/$VIDEO_ID?$SECURE_PARAMS" \
171|171|    -H "$AUTH" \
172|172|    -H "Accept: application/json" \
173|173|    2>/dev/null)
174|174|
175|175|  PLAYER_URL=$(echo "$VIDEO_DATA" | jq -r '.data.player_url // empty')
176|176|  HLS_URL=$(echo "$VIDEO_DATA" | jq -r '.data.hls_playlist // empty')
177|177|
178|178|  if [ -n "$PLAYER_URL" ]; then
179|179|    echo "$PLAYER_URL" > "$PLAYER_URL_FILE"
180|180|    echo "$VIDEO_DATA" | jq '{
181|181|      video_id: .data.id,
182|182|      title: .data.title,
183|183|      player_url: .data.player_url,
184|184|      hls_playlist: .data.hls_playlist,
185|185|      dash_playlist: .data.dash_playlist,
186|186|      thumbnail_url: .data.thumbnail_url,
187|187|      expire_time: '"$SECURE_EXPIRE"',
188|188|      uploaded_at: "'"$(date -u +%FT%TZ)"'"
189|189|    }' > "$PLAYER_JSON_FILE"
190|190|
191|191|    echo "[SECURE] $UUID — player URL saved"
192|192|    echo "         $PLAYER_URL"
193|193|    echo "         Expires: $(date -d "@$SECURE_EXPIRE" '+%Y-%m-%d %H:%M:%S')"
194|194|  else
195|195|    echo "[WARN] $UUID — no player_url in response (video may still be processing)"
196|196|  fi
197|197|else
198|198|  echo "[INFO] $UUID — ARVAN_SECURE_LINK_KEY not set, skipping secure link generation"
199|199|fi
200|200|
201|201|# ═══════════════════════════════════════════════════════════════
202|202|# DONE
203|203|# ═══════════════════════════════════════════════════════════════
204|204|echo "$(date -u +%FT%TZ)" > "$MARKER"
205|205|echo "[DONE] $UUID — $TITLE"
206|206|