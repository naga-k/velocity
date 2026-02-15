#!/bin/bash
set -e

# Sync initial memory files to persistent volume if they don't exist
MEMORY_VOL="/app/data/memory"

if [ ! -d "$MEMORY_VOL" ]; then
    echo "Initializing memory directory in persistent volume..."
    mkdir -p "$MEMORY_VOL"
    cp -r /app/memory/* "$MEMORY_VOL/" 2>/dev/null || true
    echo "Memory files synced to $MEMORY_VOL"
else
    echo "Memory directory already exists at $MEMORY_VOL"
fi

# Start the application
exec "$@"
