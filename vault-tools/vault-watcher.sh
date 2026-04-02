#!/bin/bash
# vault-watcher.sh — Obsidian vault watcher for RuVector live embedding
# Watches /home/openclaw/obsidian-vault/ for .md changes, git commits, then POSTs to RuVector ingest
# ARM64-safe, debounced 5s
#
# FIX (2026-04-02): Original used `inotifywait -m` piped into `while read` inside a subshell.
# Associative arrays (PENDING_FILES, PENDING_TIMES) written inside the subshell pipe were
# invisible to the parent — every event was silently dropped. Fixed by using single-shot
# inotifywait (no -m flag) in a loop: each call blocks until one event arrives, returns to
# the parent shell, and the parent owns the arrays the whole time.

VAULT_DIR="/home/openclaw/obsidian-vault"
LOG_FILE="/var/log/vault-watcher.log"
INGEST_URL="http://localhost:8082/ingest"
EMBED_HEALTH_URL="http://localhost:8082/health"
EMBED_FLAG_FILE="/tmp/vault-watcher-embed-down"
EMBED_HEALTH_INTERVAL=300  # seconds between periodic health checks
DEBOUNCE_SECS=5

# Ensure log file exists and is writable
touch "$LOG_FILE" 2>/dev/null || true

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [vault-watcher] $*" >> "$LOG_FILE"
}

err() {
    log "ERROR: $*"
}

# Sanity check: vault dir exists
if [[ ! -d "$VAULT_DIR" ]]; then
    err "Vault directory $VAULT_DIR does not exist"
    exit 1
fi

# Sanity check: is a git repo
if [[ ! -d "$VAULT_DIR/.git" ]]; then
    err "Vault is not a git repository. Run: cd $VAULT_DIR && git init"
    exit 1
fi

# --- Embed endpoint health check ---
# Returns 0 if healthy, 1 if down.
# Manages the flag file and logs CRITICAL/RECOVERY transitions.
# Call before ingest attempts and on the periodic timer.
LAST_EMBED_HEALTH_CHECK=0

check_embed_health() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$EMBED_HEALTH_URL" 2>/dev/null)

    if [[ "$http_code" =~ ^2 ]]; then
        # Endpoint is up — clear flag file if it was set (recovery)
        if [[ -f "$EMBED_FLAG_FILE" ]]; then
            rm -f "$EMBED_FLAG_FILE"
            log "RECOVERY: embed_ingest.py ($EMBED_HEALTH_URL) is back up (HTTP $http_code)"
        fi
        LAST_EMBED_HEALTH_CHECK=$(date +%s)
        return 0
    else
        # Endpoint is down — write flag file and log CRITICAL (once per transition)
        if [[ ! -f "$EMBED_FLAG_FILE" ]]; then
            log "CRITICAL: embed_ingest.py ($EMBED_HEALTH_URL) is not responding (HTTP ${http_code:-no response}) — writing flag $EMBED_FLAG_FILE"
            touch "$EMBED_FLAG_FILE"
        fi
        LAST_EMBED_HEALTH_CHECK=$(date +%s)
        return 1
    fi
}

log "Starting vault watcher on $VAULT_DIR"

# Track pending files for debouncing
declare -A PENDING_FILES
declare -A PENDING_TIMES

process_file() {
    local filepath="$1"
    local filename
    filename=$(basename "$filepath")

    log "Processing: $filepath"

    # --- Git commit ---
    (
        cd "$VAULT_DIR" || exit 1
        git add "$filepath" 2>/dev/null
        # Check if there are staged changes
        if git diff --cached --quiet; then
            log "No changes to commit for $filename"
        else
            git commit -m "vault-watcher: auto-commit $filename" 2>/dev/null
            if [[ $? -eq 0 ]]; then
                log "Git commit successful: $filename"
            else
                err "Git commit failed for $filename"
            fi
        fi
    )
    if [[ $? -ne 0 ]]; then
        err "Git operation failed for $filepath"
        return 1
    fi

    # --- Extract section from first H1/H2 ---
    local section
    section=$(grep -m1 -E '^#{1,2}[[:space:]]' "$filepath" 2>/dev/null | sed 's/^#*[[:space:]]*//' | tr -d '\n')
    if [[ -z "$section" ]]; then
        section="(no heading)"
    fi

    # --- Read file content ---
    local content
    content=$(cat "$filepath" 2>/dev/null)
    if [[ -z "$content" ]]; then
        err "Could not read file content: $filepath"
        return 1
    fi

    # --- Build context string (for pplx-embed-context-w8a8 contextual embedding) ---
    local context="Obsidian vault note: $filename, section: $section, vault: personal knowledge base"

    # --- POST to RuVector ingest ---
    # Payload: JSON with file content and context string
    local payload
    payload=$(printf '%s' "$(cat <<EOF
{
  "content": $(printf '%s' "$content" | jq -Rs .),
  "context": $(printf '%s' "$context" | jq -Rs .),
  "metadata": {
    "filename": $(printf '%s' "$filename" | jq -Rs .),
    "section": $(printf '%s' "$section" | jq -Rs .),
    "source": "obsidian-vault",
    "commit": "$(cd "$VAULT_DIR" && git rev-parse HEAD 2>/dev/null)"
  }
}
EOF
)" 2>/dev/null)

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$INGEST_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)

    if [[ "$http_code" =~ ^2 ]]; then
        log "Ingest OK ($http_code): $filename"
    else
        err "Ingest failed ($http_code): $filename — payload size: ${#payload} bytes"
    fi
}

# --- Debounce loop ---
# Single-shot inotifywait (no -m): blocks until one event, returns to parent shell.
# Parent owns PENDING_FILES/PENDING_TIMES the whole time — no subshell visibility issue.
# After each event, flush any files that have been pending >= DEBOUNCE_SECS.
PROCESSED=0

while true; do
    # Periodic embed health check (every EMBED_HEALTH_INTERVAL seconds)
    NOW_PRE=$(date +%s)
    if [[ $((NOW_PRE - LAST_EMBED_HEALTH_CHECK)) -ge $EMBED_HEALTH_INTERVAL ]]; then
        check_embed_health || true  # don't exit on failure — loop continues either way
    fi

    # Block until a single close_write event on a .md file
    filepath=$(inotifywait -e close_write --format '%w%f' "$VAULT_DIR" \
        --include '.*\.md$' --recursive -q 2>/dev/null)

    # Skip .git internals
    if [[ "$filepath" == *".git"* ]]; then
        continue
    fi

    # Only process actual .md files
    if [[ -z "$filepath" || "$filepath" != *.md ]]; then
        continue
    fi

    # Register the event (or refresh its timestamp if already pending)
    PENDING_FILES["$filepath"]=1
    PENDING_TIMES["$filepath"]=$(date +%s)

    # Flush any files whose debounce window has elapsed
    NOW=$(date +%s)
    for fp in "${!PENDING_FILES[@]}"; do
        FILETIME=${PENDING_TIMES["$fp"]}
        ELAPSED=$((NOW - FILETIME))
        if [[ $ELAPSED -ge $DEBOUNCE_SECS ]] && [[ -f "$fp" ]]; then
            unset PENDING_FILES["$fp"]
            unset PENDING_TIMES["$fp"]
            # Health check before each ingest attempt
            if ! check_embed_health; then
                err "Skipping ingest for $fp — embed endpoint is down"
                continue
            fi
            process_file "$fp"
            PROCESSED=$((PROCESSED + 1))
            if [[ $((PROCESSED % 20)) -eq 0 ]]; then
                log "Processed $PROCESSED files since startup"
            fi
        fi
    done
done
