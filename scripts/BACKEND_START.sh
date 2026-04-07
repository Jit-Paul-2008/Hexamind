#!/bin/bash

# 🚀 Hexamind Backend Startup Script
# Run this on your Azure VM

echo "🎯 Starting Hexamind Backend..."

# Step 1: Navigate to backend
cd /home/Jit-Paul-2008/hexamind/ai-service

# Step 2: Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Step 3: Start backend server
echo "🚀 Starting backend server..."
echo "Backend will be available at: http://localhost:8000"
echo "Health check: curl http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the backend
python main.py
