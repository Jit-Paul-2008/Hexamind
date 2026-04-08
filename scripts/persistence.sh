#!/bin/bash

# Hexamind Persistence Script
# Ensures backend and tunnel are active

WORKSPACE="/home/Jit-Paul-2008/Desktop/Hexamind"
VENV_PYTHON="$WORKSPACE/venv/bin/python3"
CLOUDFLARED="$WORKSPACE/scripts/cloudflared"

echo "[$(date)] Checking Hexamind services..."

# 1. Check Backend API (Port 8000)
if ! lsof -i :8000 > /dev/null; then
    echo "[$(date)] Backend not running. Starting..."
    cd "$WORKSPACE"
    nohup "$VENV_PYTHON" -m uvicorn main:app --app-dir ai-service --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
fi

# 2. Check Cloudflare Tunnel
if ! pgrep -f "cloudflared tunnel --url" > /dev/null; then
    echo "[$(date)] Tunnel not running. Starting..."
    cd "$WORKSPACE"
    # Ensure old log is cleared to avoid stale URL extraction
    cat /dev/null > tunnel.log
    nohup "$CLOUDFLARED" tunnel --url http://localhost:8000 > tunnel.log 2>&1 &
    
    # Wait for URL generation (Cloudflare takes a few seconds)
    echo "[$(date)] Waiting for public URL generation..."
    for i in {1..10}; do
        TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]\+\.trycloudflare\.com' tunnel.log | head -n 1)
        if [ ! -z "$TUNNEL_URL" ]; then
            echo "[$(date)] New Tunnel URL: $TUNNEL_URL"
            # Update public config for frontend discovery
            echo "{\"apiUrl\": \"$TUNNEL_URL\"}" > "$WORKSPACE/public/config.json"
            break
        fi
        sleep 2
    done
fi

echo "[$(date)] Check complete. If URL changed, please run 'npm run deploy' to update the live site."
