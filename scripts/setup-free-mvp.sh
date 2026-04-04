#!/bin/bash

#######################################
# ARIA MVP Free Setup Script
# Automates: DB password, domain, SSL, legal docs
# Requirements: openssl, sudo access
#######################################

set -e

echo "🚀 ARIA MVP Free Setup Starting..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# ===== 1. GENERATE JWT SECRET =====
echo ""
echo "📝 [1/5] Generating secure JWT secret..."
JWT_SECRET=$(openssl rand -hex 32)
echo "✅ JWT Secret generated: ${JWT_SECRET:0:8}..."

# ===== 2. GENERATE DATABASE PASSWORD =====
echo ""
echo "📝 [2/5] Generating secure database password..."
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')
echo "✅ Database password generated: ${DB_PASSWORD:0:8}..."

# ===== 3. CREATE .env FILE =====
echo ""
echo "📝 [3/5] Creating .env configuration file..."

cat > "$ENV_FILE" << EOF
# ===== ARIA MVP Configuration =====
# Generated: $(date)
# All free/open-source tools

# === APP SETTINGS ===
NODE_ENV=development
DEPLOYMENT_ENV=local
API_PORT=8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# === SECURITY ===
JWT_SECRET=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=30
REFRESH_TOKEN_EXPIRY_DAYS=7

# === DATABASE ===
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./aria.db
POSTGRES_USER=aria_user
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=aria_prod
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# === COLORS (WARM PALETTE) ===
PRIMARY_COLOR=#FF9A56
SECONDARY_COLOR=#FFB84D
DANGER_COLOR=#EF4444

# === DOMAIN & SSL ===
DOMAIN=aria.local
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/aria.local/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/aria.local/privkey.pem

# === TAVILY API (OPTIONAL) ===
# Get free key from https://tavily.com
TAVILY_API_KEY=***YOUR_KEY_HERE***

# === FEATURES ===
ENABLE_NEW_UI=false
ENABLE_DATABASE_PERSISTENCE=false
ENABLE_ADVANCED_COMPARE=true
ENABLE_TAVILY_RESEARCH=false

# === LOGGING ===
LOG_LEVEL=info
LOG_FORMAT=json

# === CORS ===
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://aria.local:3000

# === ORGANIZATION ===
ORG_NAME=ARIA Team
SUPPORT_EMAIL=support@aria.local
SECURITY_EMAIL=security@aria.local

EOF

echo "✅ .env file created at: $ENV_FILE"

# ===== 4. SETUP ARIA.LOCAL HOSTNAME =====
echo ""
echo "📝 [4/5] Configuring aria.local hostname..."

if grep -q "aria.local" /etc/hosts; then
    echo "⚠️  aria.local already in /etc/hosts, skipping..."
else
    echo "Adding aria.local to /etc/hosts (requires sudo)..."
    echo "127.0.0.1 aria.local" | sudo tee -a /etc/hosts > /dev/null
    echo "✅ aria.local configured"
fi

# ===== 5. SSL CERTIFICATE SETUP INSTRUCTIONS =====
echo ""
echo "📝 [5/5] SSL Certificate Setup..."
echo ""
echo "⚠️  Let's Encrypt setup requires manual steps (first time only):"
echo ""
echo "  1. Install certbot:"
echo "     sudo apt-get install certbot python3-certbot-nginx -y"
echo ""
echo "  2. Generate certificate:"
echo "     sudo certbot certonly --standalone -d aria.local -d www.aria.local"
echo ""
echo "  3. Auto-renewal (certbot handles this automatically)"
echo ""
echo "  📌 For development, you can skip SSL and use http://aria.local:3000"
echo ""

# ===== 6. CREATE DOCKER COMPOSE .ENV OVERRIDE =====
echo ""
echo "📝 Creating docker-compose overrides..."

cat > "$PROJECT_ROOT/docker-compose.override.yml" << 'EOF'
version: '3.8'

services:
  db:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    environment:
      DATABASE_URL: sqlite:///./aria.db
      JWT_SECRET: ${JWT_SECRET}
    ports:
      - "8000:8000"

  web:
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"

volumes:
  postgres_data:
EOF

echo "✅ docker-compose.override.yml created"

# ===== SUMMARY =====
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣  Review .env file:"
echo "    cat $ENV_FILE"
echo ""
echo "2️⃣  Add Tavily API key (optional):"
echo "    Edit .env and replace ***YOUR_KEY_HERE***"
echo "    Get free key: https://tavily.com"
echo ""
echo "3️⃣  Start development:"
echo "    source .venv/bin/activate"
echo "    docker-compose up -d"
echo "    npm run dev"
echo ""
echo "4️⃣  Access app:"
echo "    http://localhost:3000 (dev)"
echo "    http://aria.local:3000 (after SSL setup)"
echo ""
echo "🔐 Security Notes:"
echo "   • JWT Secret: ${JWT_SECRET:0:16}..."
echo "   • DB Password: ${DB_PASSWORD:0:16}..."
echo "   • Both are in .env (DO NOT COMMIT .env to git)"
echo ""
echo "📚 Docs:"
echo "   • Read ARIA_UX_ROLLOUT_PLAN.md for Phase timing"
echo "   • Check REQUIRED_USER_INPUTS.md for configuration"
echo ""
