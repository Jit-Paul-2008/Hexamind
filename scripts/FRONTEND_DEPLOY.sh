#!/bin/bash

# 🚀 Hexamind Frontend Deployment Script
# Run this on your LOCAL computer (not the VM)

echo "🎯 Starting Hexamind Frontend Deployment..."

# Step 1: Navigate to project
cd /home/Jit-Paul-2008/Desktop/Hexamind

# Step 2: Install dependencies
echo "📦 Installing dependencies..."
npm install

# Step 3: Configure to connect to your VM backend
echo "🔧 Configuring API connection..."
echo "Enter your VM's Public IP address:"
read VM_IP

echo "NEXT_PUBLIC_API_URL=http://$VM_IP:8000" > .env.local

# Step 4: Build frontend
echo "🏗️ Building frontend..."
npm run build

# Step 5: Deploy to GitHub Pages
echo "🌐 Deploying to GitHub Pages..."
npx gh-pages -d out -b main

# Step 6: Success!
echo "✅ DEPLOYMENT COMPLETE!"
echo "🌐 Your site is live at: https://Jit-Paul-2008.github.io/hexamind"
echo "🎯 Test your AI research company now!"
