# ARIA MVP Free Setup Guide

**Generated:** April 4, 2026  
**Status:** Ready to deploy  
**Cost:** $0 (100% free tools)

---

## 🚀 Quick Start (5 minutes)

### Step 1: Run the automated setup script

```bash
cd /home/Jit-Paul-2008/Desktop/Hexamind
bash scripts/setup-free-mvp.sh
```

**This will automatically:**
✅ Generate a secure JWT secret  
✅ Generate a secure database password  
✅ Create `.env` configuration file  
✅ Configure `aria.local` in `/etc/hosts`  
✅ Create Docker Compose overrides  

### Step 2: Review the generated `.env` file

```bash
cat .env
```

**Important**: You'll see output like:
```
JWT_SECRET=a1b2c3d4e5f6g7h8...
POSTGRES_PASSWORD=XyZ123+456/789=...
```

These are safely stored in `.env` (not in git).

### Step 3: Start developing

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already done)
python -m pip install -r ai-service/requirements.txt
npm install

# If Docker is not installed on this Linux VM
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker

# Start the development stack
sudo docker compose up -d

# Run the app
npm run dev
```

Access at: **http://localhost:3000**

---

## 📋 What Was Set Up

### Configuration Files Created

| File | Purpose | Location |
|------|---------|----------|
| `.env` | Secrets & settings (NOT in git) | Project root |
| `.env.example` | Template (tracked in git) | Project root |
| `docker-compose.override.yml` | Local dev overrides | Project root |
| `PRIVACY_POLICY.md` | Legal doc (GDPR-compliant) | `src/docs/` |
| `TERMS_OF_SERVICE.md` | Legal doc | `src/docs/` |
| `SECURITY_POLICY.md` | Security disclosure | `src/docs/` |

### Passwords & Secrets (Auto-Generated)

```
✅ JWT Secret       : 32-char random string       (in .env)
✅ DB Password      : 24-char base64 random      (in .env)
✅ aria.local       : configured in /etc/hosts   (127.0.0.1)
```

### Database

- **Development**: SQLite (auto-created, in-memory option available)
- **Production**: PostgreSQL ready (credentials in .env)
- **Tests**: SQLite in-memory transactions

---

## 🔐 Security

### Credentials Management

```bash
# View JWT secret
grep JWT_SECRET .env

# View DB password
grep POSTGRES_PASSWORD .env

# Never commit .env to git!
echo ".env" >> .gitignore
git add .gitignore && git commit -m "Add .env to gitignore"
```

### SSL Certificate (Optional, Phase 2)

For local development, HTTP is fine. For production:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx -y

# Generate certificate
sudo certbot certonly --standalone -d aria.local

# Update .env
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/aria.local/fullchain.pem
```

---

## 📦 Free Tools Included

### Database
- **SQLite** (development) — Built-in, zero setup
- **PostgreSQL** (production) — Free, open-source

### Authentication
- **JWT** — JSON Web Tokens, built-in
- **bcrypt** — Password hashing, secure

### API Research
- **Tavily** — Free tier ~10 searches/month
  - Optional, skipped in MVP
  - Edit `.env` to add key later

### AI Models
- **Ollama** — Free, local LLMs
  - Run locally on your machine
  - No external API calls
  - Models: qwen2.5-coder, llama2, etc.

### Web Framework
- **Next.js** — React framework, free
- **FastAPI** — Python API, free
- **Docker** — Containerization, free

### Infrastructure
- **Docker Compose** — Orchestration (free)
- **Nginx** — Reverse proxy (free)
- **Let's Encrypt** — SSL certs (free)

---

## 📚 What to Do Next

### Immediate (Phase 1)

- [ ] Confirm warm colors are good (`#FF9A56`, `#FFB84D`, `#EF4444`)
- [ ] Start building UI components
- [ ] Test database operations

### Short-term (Phase 2-3)

- [ ] Get Tavily API key (optional, $~10/month)
  - Sign up: https://tavily.com
  - Add to `.env`: `TAVILY_API_KEY=tvly-...`
- [ ] Set up PostgreSQL if needed (Django migrations)
- [ ] Configure Docker registry (Docker Hub, ECR, or skip)

### Before Production (Phase 4+)

- [ ] Update legal docs with your org name
- [ ] Set up SSL certificate (Let's Encrypt)
- [ ] Configure email service (SendGrid, Mailgun, or skip)
- [ ] Test authentication flow
- [ ] Review and sign off on security policy

---

## 🛠️ Troubleshooting

### Issue: `aria.local` not working

**Solution:**
```bash
# Check if it's in /etc/hosts
grep aria.local /etc/hosts

# If not, add it manually
echo "127.0.0.1 aria.local" | sudo tee -a /etc/hosts

# Flush DNS cache
sudo systemctl restart systemd-resolved
```

### Issue: JWT secret is missing

**Solution:** Re-run setup script
```bash
bash scripts/setup-free-mvp.sh
```

### Issue: Docker Compose fails

**Solution:** Check ports are available
```bash
# If command not found, install Docker first
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker

# Check port 8000 and 3000
sudo netstat -tulpn | grep -E ":(3000|8000)"

# Kill process if needed
sudo lsof -ti:3000 | xargs kill -9

# Start stack using plugin command
sudo docker compose up -d
```

### Issue: Can't connect to Ollama

**Solution:** Install Ollama first
```bash
# Download from https://ollama.ai
# Or install: curl https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull qwen2.5-coder:1.5b-base
```

---

## 📖 References

- **Project Structure**: See `PROJECT_STRUCTURE.md`
- **Architecture**: See `ARCHITECTURE_DECISIONS.md`
- **Rollout Plan**: See `ARIA_UX_ROLLOUT_PLAN.md`
- **Configuration**: See `REQUIRED_USER_INPUTS.md`
- **Legal**: See `src/docs/` folder

---

## ❓ FAQ

**Q: Is this secure for production?**

A: The setup is secure *for development*. For production:
- Use a managed PostgreSQL (AWS RDS, Heroku, etc.)
- Enable SSL/TLS with Let's Encrypt
- Add rate limiting and authentication
- Set up monitoring and alerts
- Review security policies with your team

**Q: Why free tools?**

A: To get you started with zero cost. You can upgrade to paid services as you grow:
- Tavily → other research APIs
- Ollama → OpenAI, Anthropic, etc.
- SQLite → managed PostgreSQL
- Docker Compose → Kubernetes
- Email → SendGrid, Mailgun

**Q: Can I use a different database?**

A: Yes! Just update `DATABASE_URL` in `.env`:
- SQLite: `sqlite:///./aria.db`
- PostgreSQL: `postgresql://user:pass@localhost/dbname`
- MySQL: `mysql://user:pass@localhost/dbname`

**Q: How do I update the legal docs?**

A: Edit the `.md` files in `src/docs/`:
```bash
vim src/docs/PRIVACY_POLICY.md
```

Add your actual organization name, legal contact, etc.

---

## 📞 Support

For setup issues:
1. Check the [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
2. Review error messages in `.env`
3. Run setup script again: `bash scripts/setup-free-mvp.sh`

For security concerns:
- Email: `security@aria.local`

---

**Setup Version**: 1.0 MVP  
**Last Updated**: April 4, 2026
