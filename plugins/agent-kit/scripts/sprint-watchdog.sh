#!/usr/bin/env bash
# Keep an unattended sprint moving when the session driving it dies.
#
#   sprint-watchdog.sh <sprint directory>
#
# Started detached by `sprint` at preflight and left to outlive the orchestrator, a rate-limit stop
# and a dropped connection. It resumes the sprint — `claude -p "/agent-kit:sprint"` reads the queue
# and continues — and exits by itself once the queue says `done`.
#
# Liveness is measured by work, not by process existence. A `claude -p` child that hit a limit can
# stay in the process table indefinitely; an earlier version of this watchdog matched it with pgrep,
# concluded a run was in flight, and skipped every tick in silence for six hours. So a process only
# counts as alive if its own log has grown recently, and every tick is logged, including the quiet
# ones — a watchdog whose silence is ambiguous is worse than none.
set -u

SPRINT="${1:?usage: sprint-watchdog.sh <sprint directory>}"
QUEUE="$SPRINT/queue.yml"
HEARTBEAT="$SPRINT/heartbeat"
LOG="$SPRINT/watchdog.log"

INTERVAL=300              # look every five minutes
STALE=1500                # heartbeat older than this means nobody is recording transitions
WORKING=1200              # a child's log untouched this long is a hung process, not a run
MAX_LIFETIME=$((48 * 3600))

started=$(date +%s)
echo $$ > "$SPRINT/watchdog.pid"
log() { printf '%s  %s\n' "$(date -Is)" "$1" >> "$LOG"; }

# Seconds until the reset hour a rate-limited child names in its output, or 0 if it named none.
# "You've hit your session limit · resets 10:40am" — wait for that rather than burning a session
# start every five minutes against a closed window.
until_reset() {
  local when
  when=$(tail -5 "$1" 2>/dev/null | grep -o 'resets [0-9:apm ]*' | tail -1 | cut -d' ' -f2-)
  [ -n "$when" ] || { echo 0; return; }
  local target now
  target=$(date -d "$when" +%s 2>/dev/null) || { echo 0; return; }
  now=$(date +%s)
  [ "$target" -le "$now" ] && target=$((target + 86400))   # named an hour already past today
  echo $((target - now))
}

log "up (pid $$), watching $SPRINT"

while sleep "$INTERVAL"; do
  now=$(date +%s)

  if [ $((now - started)) -gt "$MAX_LIFETIME" ]; then log "max lifetime reached — exiting"; break; fi
  if [ ! -f "$QUEUE" ]; then log "queue is gone — exiting"; break; fi
  if grep -q '^status: *done' "$QUEUE"; then log "sprint is done — exiting"; break; fi

  # A child counts as working only if it is both present and producing output.
  working=""
  for pid in $(pgrep -f '/agent-kit:s' 2>/dev/null); do
    [ "$pid" = "$$" ] && continue
    for f in "$SPRINT"/*/run.log; do
      [ -f "$f" ] || continue
      if [ $((now - $(stat -c %Y "$f"))) -lt "$WORKING" ]; then working="$f"; break 2; fi
    done
  done
  if [ -n "$working" ]; then log "a run is working ($working) — nothing to do"; continue; fi

  if [ -f "$HEARTBEAT" ]; then age=$((now - $(stat -c %Y "$HEARTBEAT"))); else age=$((STALE + 1)); fi
  if [ "$age" -le "$STALE" ]; then log "orchestrator alive (heartbeat ${age}s) — nothing to do"; continue; fi

  wait_for=$(until_reset "$SPRINT/resume.log")
  if [ "$wait_for" -gt 0 ]; then
    log "rate limit until reset in ${wait_for}s — sleeping"
    sleep "$wait_for"
    continue
  fi

  log "no live run and heartbeat is ${age}s old — resuming the sprint"
  (cd "${SPRINT%/.agent-kit/sprint/*}" && claude -p "/agent-kit:sprint" \
     --permission-mode bypassPermissions) >> "$SPRINT/resume.log" 2>&1
  log "resume attempt ended with exit $?"
done

rm -f "$SPRINT/watchdog.pid"
log "down"
