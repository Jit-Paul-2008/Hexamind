#!/bin/bash

# ARIA MVP Free Setup — Completion Verification
# Run this to verify all setup files are in place

echo ""
echo "🔍 ARIA MVP Setup Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROJECT_ROOT"

# Check files
FILES_TO_CHECK=(
    ".env"
    ".env.example"
    "docker-compose.override.yml"
    "src/docs/PRIVACY_POLICY.md"
    "src/docs/TERMS_OF_SERVICE.md"
    "src/docs/SECURITY_POLICY.md"
    "SETUP_GUIDE.md"
    "REQUIRED_USER_INPUTS.md"
)

CHECKS_PASSED=0
CHECKS_FAILED=0

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
        ((CHECKS_PASSED++))
    else
        echo "❌ $file (MISSING)"
        ((CHECKS_FAILED++))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check .env contents
if [ -f ".env" ]; then
    if grep -q "JWT_SECRET=" .env && grep -q "POSTGRES_PASSWORD=" .env; then
        echo "✅ .env contains required secrets"
        echo ""
        echo "🔐 Secret Status:"
        echo "   JWT Secret: $(grep JWT_SECRET .env | cut -d= -f2 | cut -c1-16)..."
        echo "   DB Password: $(grep POSTGRES_PASSWORD .env | cut -d= -f2 | cut -c1-16)..."
    fi
fi

echo ""

# Check aria.local in /etc/hosts
if grep -q "aria.local" /etc/hosts; then
    echo "✅ aria.local configured in /etc/hosts"
else
    echo "❌ aria.local NOT in /etc/hosts (run setup again)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✅ All setup files are in place!"
    echo ""
    echo "🚀 You're ready to start developing!"
    echo ""
    echo "Next steps:"
    echo "  1. source .venv/bin/activate"
    echo "  2. docker-compose up -d"
    echo "  3. npm run dev"
    echo "  4. Visit http://localhost:3000"
else
    echo "⚠️  $CHECKS_FAILED file(s) missing"
    echo "Re-run setup: bash scripts/setup-free-mvp.sh"
fi

echo ""
