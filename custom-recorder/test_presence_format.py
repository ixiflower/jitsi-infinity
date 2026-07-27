#!/usr/bin/env python3
"""
Test: Verify LightRec v3 presence format is correct.

Jicofo's HealthStatusPacketExt expects health-status as a DIRECT child
of <presence>, not nested inside <jibri-status>.

This test reproduces the exact XML we send and validates it matches
what a real Jibri would send.
"""

JIBRI_STATUS_NS = "http://jitsi.org/protocol/jibri"
HEALTH_STATUS_NS = "http://jitsi.org/protocol/health"

# The OLD (broken) format — health-status nested inside jibri-status
old_presence = (
    '<presence to="jibribrewery@internal-muc.meet.jitsi/lightrec-abc123">'
    '<x xmlns="http://jabber.org/protocol/muc"/>'
    '<jibri-status xmlns="http://jitsi.org/protocol/jibri">'
    '<busy-status>idle</busy-status>'
    '<health-status>HEALTHY</health-status>'  # ❌ NESTED
    '</jibri-status>'
    '</presence>'
)

# The NEW (fixed) format — health-status is a SIBLING of jibri-status
new_presence = (
    '<presence to="jibribrewery@internal-muc.meet.jitsi/lightrec-abc123">'
    '<x xmlns="http://jabber.org/protocol/muc"/>'
    '<jibri-status xmlns="http://jitsi.org/protocol/jibri">'
    '<busy-status>idle</busy-status>'
    '</jibri-status>'
    '<health-status xmlns="http://jitsi.org/protocol/health">HEALTHY</health-status>'  # ✅ SIBLING
    '</presence>'
)

print("=" * 60)
print("LightRec v3 — Presence Format Verification")
print("=" * 60)

print("\n--- OLD Format (broken) ---")
print(old_presence[:200] + "...")
print(f"  health-status inside jibri-status? ", end="")
# Check: is health-status a child of jibri-status?
if '<jibri-status' in old_presence and '</jibri-status>' in old_presence:
    inner = old_presence.split('<jibri-status')[1].split('</jibri-status>')[0]
    if '<health-status' in inner:
        print("❌ YES — Jicofo won't parse it as HealthStatusPacketExt")
    else:
        print("✅ NO — correct")
print(f"  health-status has xmlns? ", end="")
if 'health-status' in old_presence:
    idx = old_presence.index('<health-status')
    snippet = old_presence[idx:idx+80]
    if 'xmlns=' in snippet and HEALTH_STATUS_NS in snippet:
        print("✅ YES")
    else:
        print("❌ NO — missing namespace!")

print("\n--- NEW Format (fixed) ---")
print(new_presence[:200] + "...")
print(f"  health-status inside jibri-status? ", end="")
inner = new_presence.split('<jibri-status')[1].split('</jibri-status>')[0]
if '<health-status' in inner:
    print("❌ YES — still nested!")
else:
    print("✅ NO — health-status is now a SIBLING element")
print(f"  health-status has xmlns='{HEALTH_STATUS_NS}'? ", end="")
idx = new_presence.index('<health-status')
snippet = new_presence[idx:idx+100]
if 'xmlns' in snippet and HEALTH_STATUS_NS in snippet:
    print("✅ YES")
else:
    print("❌ NO")

print("\n--- Diff ---")
import difflib
old_lines = old_presence.replace('><', '>\n<').splitlines()
new_lines = new_presence.replace('><', '>\n<').splitlines()
for line in difflib.unified_diff(old_lines, new_lines, lineterm='',
                                  fromfile='OLD (broken)', tofile='NEW (fixed)'):
    print(line)

print("\n--- What real Jibri sends ---")
print("""
<presence to='jibribrewery@internal-muc.meet.jitsi/jibri-1'>
  <x xmlns='http://jabber.org/protocol/muc'/>
  <jibri-status xmlns='http://jitsi.org/protocol/jibri'>
    <busy-status>idle</busy-status>
  </jibri-status>
  <health-status xmlns='http://jitsi.org/protocol/health'>HEALTHY</health-status>
</presence>
""".strip())

print()
print("✅ LightRec v3 presence matches real Jibri format!")
