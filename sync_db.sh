#!/usr/bin/env bash
# Copy the newest nightly backup off the NAS into this folder, so an occasional
# read-only snapshot of the live DB can be committed into the repo.
# Usage: ./sync_db.sh   (override the host with NAS_HOST=... if not "mynas")
set -euo pipefail

NAS="${NAS_HOST:-mynas}"
REMOTE_DIR="/volume1/docker/tripsite/backup"
HERE="$(cd "$(dirname "$0")" && pwd)"

latest=$(ssh "$NAS" "ls -1t $REMOTE_DIR/trip-*.db 2>/dev/null | head -1")
if [ -z "$latest" ]; then
  echo "No backups found in $NAS:$REMOTE_DIR" >&2
  exit 1
fi

scp "$NAS:$latest" "$HERE/trip-backup.db"
echo "Synced $(basename "$latest") -> trip-backup.db"
