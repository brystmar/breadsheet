#!/bin/bash
# Weekly backup of breadsheet's production Postgres (Neon) to the NAS (Second Rise item 5b).
# Runs as a TrueNAS cron job; see "Backups" in CLAUDE.md for setup and restore.
#
# Usage: backup_postgres.sh <backup_dir> <credentials_file>
#
# <credentials_file> is a libpq env file for the read-only `breadsheet_backup` role, readable only
# by its owner (chmod 600). It's passed to Docker with --env-file, so the password never appears in
# a process list:
#   PGHOST=<production endpoint host, without -pooler>
#   PGDATABASE=neondb
#   PGUSER=breadsheet_backup
#   PGPASSWORD=<password>
#   PGSSLMODE=require
#
# Each run writes breadsheet-<UTC timestamp>.dump (pg_dump custom format), checks that it's a
# readable archive, and only then deletes all but the newest $KEEP dumps. Errors go to stderr with a
# non-zero exit, so the cron job's email (or other alert) fires; success prints one line.
#
# Exit codes, so a failure is identifiable even where only the code is shown (e.g. TrueNAS "Run Now"):
#   2  bad arguments, or the credentials file is readable by others
#   3  pg_dump failed: Docker unavailable, can't connect, or login refused
#   4  the dump isn't a readable archive
#   5  the dump has no recipes table (e.g. an empty database)
set -euo pipefail

# The client's major version must be >= the server's (Neon production runs Postgres 18)
PG_IMAGE=${PG_IMAGE:-postgres:18.6}
KEEP=${KEEP:-12}

if [ $# -ne 2 ]; then
    echo "Usage: $0 <backup_dir> <credentials_file>" >&2
    exit 2
fi
BACKUP_DIR=$1
CREDENTIALS=$2

# Refuse a credentials file that anyone but its owner can read (GNU stat on TrueNAS, BSD stat on macOS)
PERMS=$(stat -c %a "$CREDENTIALS" 2>/dev/null || stat -f %Lp "$CREDENTIALS")
if [ "${PERMS: -2}" != "00" ]; then
    echo "Credentials file $CREDENTIALS has mode $PERMS; run: chmod 600 $CREDENTIALS" >&2
    exit 2
fi

mkdir -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TARGET="$BACKUP_DIR/breadsheet-$STAMP.dump"
PARTIAL="$TARGET.partial"
trap 'rm -f "$PARTIAL"' EXIT

# Dump to a temporary name, so a failed run never leaves a file that looks like a good backup
if ! docker run --rm --env-file "$CREDENTIALS" "$PG_IMAGE" \
        pg_dump --format=custom --no-owner --no-acl > "$PARTIAL"; then
    echo "pg_dump failed (see the error above); keeping the existing backups" >&2
    exit 3
fi

# Confirm it's a readable archive that contains the recipes table before keeping it
if ! CONTENTS=$(docker run --rm -i "$PG_IMAGE" pg_restore --list < "$PARTIAL"); then
    echo "Dump isn't a readable archive (see the error above); keeping the existing backups" >&2
    exit 4
fi
TABLES=$(grep -c " TABLE public " <<< "$CONTENTS" || true)
if ! grep -q " TABLE public recipes " <<< "$CONTENTS"; then
    echo "Dump has no recipes table ($TABLES tables); keeping the existing backups" >&2
    exit 5
fi
mv "$PARTIAL" "$TARGET"

# Keep the newest $KEEP dumps; timestamped names sort chronologically
PRUNED=0
while IFS= read -r old; do
    rm -f -- "$old"
    PRUNED=$((PRUNED + 1))
done < <(ls -1 "$BACKUP_DIR"/breadsheet-*.dump | sort -r | tail -n +$((KEEP + 1)))

SIZE=$(du -h "$TARGET" | cut -f1)
echo "Backed up breadsheet to $TARGET ($SIZE, $TABLES tables); pruned $PRUNED old dump(s)"
