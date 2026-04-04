#!/bin/bash
# 1. Start Backend
source .venv/bin/activate
export HEXAMIND_DISABLE_FAILSAFE_FALLBACK=0
python3 -m uvicorn main:app --app-dir ai-service --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 2. Wait for backend
sleep 4

# 3. Start lt for backend
lt --port 8000 > backend_url.txt &
LT_BACKEND_PID=$!

sleep 4
BACKEND_URL=$(cat backend_url.txt | awk '{print $4}')
echo "Backend URL: $BACKEND_URL"

# 4. update frontend env
echo "NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL" > .env.local
echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" >> .env.local

# 6. Start frontend
/usr/local/bin/npm run dev &
FRONTEND_PID=$!

sleep 4

# 7. Start lt for frontend
lt --port 3000 > frontend_url.txt &
LT_FRONTEND_PID=$!

sleep 4
FRONTEND_URL=$(cat frontend_url.txt | awk '{print $4}')

echo ""
echo "================================================="
echo " LIVE DEPLOYMENT LINKS "
echo "================================================="
echo " Backend URL: $BACKEND_URL "
echo " Frontend URL: $FRONTEND_URL "
echo "================================================="
echo "Send the Frontend URL to your users!"

wait
