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
# For Quick Tunnels, we check if the process exists. 
# In a real Named Tunnel, we'd use 'cloudflared tunnel run'.
if ! pgrep -f "cloudflared tunnel --url" > /dev/null; then
    echo "[$(date)] Tunnel not running. Starting..."
    cd "$WORKSPACE"
    nohup "$CLOUDFLARED" tunnel --url http://localhost:8000 > tunnel.log 2>&1 &
fi

echo "[$(date)] Check complete."
