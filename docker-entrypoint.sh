#!/bin/bash
set -e

# Initialize feeds.json if not exists in volume
if [ ! -f /app/data/feeds.json ]; then
    echo "Initializing feeds.json from defaults..."
    if [ -f /app/defaults/feeds.json ]; then
        cp /app/defaults/feeds.json /app/data/feeds.json
        echo "✅ Copied default feeds ($(wc -l < /app/defaults/feeds.json) lines)"
    else
        echo "[]" > /app/data/feeds.json
        echo "⚠️  No defaults found, created empty feeds.json"
    fi
else
    echo "✅ feeds.json already exists in volume"
fi

# Execute the main application
exec "$@"
