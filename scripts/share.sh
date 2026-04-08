#!/bin/bash

# Hexamind Share Dashboard
# A simple, non-technical status checker

WORKSPACE="/home/Jit-Paul-2008/Desktop/Hexamind"
TUNNEL_LOG="$WORKSPACE/tunnel.log"
PUBLIC_LINK="https://Jit-Paul-2008.github.io/Hexamind/"

echo -e "\033[1;34m🛰️  Hexamind: Public Status Dashboard\033[0m"
echo "------------------------------------------------"

# 1. Check Ollama
if pgrep -x "ollama" > /dev/null || pgrep -f "ollama serve" > /dev/null; then
    echo -e "🧠 Models (Ollama): \033[0;32mONLINE\033[0m"
else
    echo -e "🧠 Models (Ollama): \033[0;31mOFFLINE\033[0m (Run 'ollama serve')"
fi

# 2. Check Backend
if lsof -i :8000 > /dev/null; then
    echo -e "⚙️  Research Backend: \033[0;32mONLINE\033[0m"
else
    echo -e "⚙️  Research Backend: \033[0;31mOFFLINE\033[0m (Run './scripts/persistence.sh')"
fi

# 3. Check Tunnel & URL
TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]\+\.trycloudflare\.com' "$TUNNEL_LOG" | head -n 1)
if pgrep -f "cloudflared tunnel" > /dev/null && [ ! -z "$TUNNEL_URL" ]; then
    echo -e "🌐 Public Tunnel:    \033[0;32mACTIVE\033[0m"
    echo -e "   ↳ Endpoint:       \033[0;36m$TUNNEL_URL\033[0m"
else
    echo -e "🌐 Public Tunnel:    \033[0;31mINACTIVE\033[0m"
fi

echo "------------------------------------------------"
echo -e "\033[1;32m🚀 YOUR LIVE LINK:\033[0m"
echo -e "\033[1;37m$PUBLIC_LINK\033[0m"
echo "------------------------------------------------"
echo "Share the link above! People can use Hexamind as"
echo "long as this terminal and your computer stay on."
