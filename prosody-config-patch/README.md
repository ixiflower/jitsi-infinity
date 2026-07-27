# LightRec — Required Prosody Config Changes
# ============================================
# Apply these to /run/prosody/config/conf.d/jitsi-meet.cfg.lua
# inside the jitsi-prosody container (or copy from host).
#
# These changes tell Jicofo that jibri@auth.meet.jitsi is a valid
# recorder domain, allow it past MUC password walls, and disable
# the resource validation that blocks custom MUC nicknames.

## 1. recorder_prefixes — ADD jibri@auth.meet.jitsi
## Without this, Jicofo won't allocate colibri channels when
## LightRec joins the conference room with Jibri status presence.
##
## Find this line (near the top of jitsi-meet.cfg.lua):
##   recorder_prefixes = { "recorder@hidden.meet.jitsi" };
##
## Change to:
##   recorder_prefixes = { "recorder@hidden.meet.jitsi", "jibri@auth.meet.jitsi" };


## 2. muc_password_whitelist — ADD jibri@auth.meet.jitsi
## If the meeting room is password-protected, LightRec's MUC join
## will be rejected unless jibri is whitelisted.
##
## Find this line:
##   muc_password_whitelist = {
##       "focus@auth.meet.jitsi";
##       "recorder@hidden.meet.jitsi";
##   }
##
## Change to:
##   muc_password_whitelist = {
##       "focus@auth.meet.jitsi";
##       "recorder@hidden.meet.jitsi";
##       "jibri@auth.meet.jitsi";
##   }


## 3. muc_resource_validate — REMOVE (or disable)
## If jitsi-meet.cfg.lua has:
##   modules_enabled = {
##       "muc_hide_all";
##       "muc_meeting_id";
##       "muc_domain_mapper";
##       "muc_password_whitelist";
##       "muc_resource_validate";   <-- REMOVE this line
##   }
##
## Comment it out:
##   -- "muc_resource_validate";  <-- REMOVED to allow Jibri/LightRec custom MUC resources


## How to apply
## =============
## Option A — edit inside the container:
##   docker exec -it jitsi-prosody sed -i \
##     's/recorder_prefixes = { "recorder@hidden.meet.jitsi" }/recorder_prefixes = { "recorder@hidden.meet.jitsi", "jibri@auth.meet.jitsi" }/' \
##     /run/prosody/config/conf.d/jitsi-meet.cfg.lua
##   docker compose restart prosody
##
## Option B — copy from host:
##   docker cp ~/jitsi-infinity/prosody-config-patch/jitsi-meet.cfg.lua jitsi-prosody:/run/prosody/config/conf.d/jitsi-meet.cfg.lua
##   docker compose restart prosody
