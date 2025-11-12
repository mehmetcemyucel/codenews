# 🚀 Deployment Guide (English)

This document explains how to deploy CodeNews with Docker, GitHub Actions, or plain SSH. The project is distributed under the Apache License 2.0 (`LICENSE`).

## 1. Prerequisites
- Docker Engine + Docker Compose (v2+ recommended)
- GitHub account with Actions enabled
- VPS or server with SSH access (Ubuntu/Debian examples below)
- Telegram bot token + chat ID

## 2. Environment & Secrets
Store secrets in one place (GitHub → *Settings → Secrets and variables → Actions* or `.env` on your server).

| Key | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | Chat/channel receiving notifications |
| `OPENAI_API_KEY` | optional | Enables LLM summaries |
| `DATABASE_URL` | optional | Use Postgres instead of SQLite |
| `TIMEZONE`, `LOG_LEVEL` | optional | Overrides defaults |
| `RSS_CHECK_INTERVAL_HOURS`, `MAX_ITEMS_PER_FEED`, ... | optional | Any numeric config knob from `config.yaml` |
| `BLOG_MIN_ITEMS`, `BLOG_MAX_ITEMS`, `BLOG_SCHEDULE_*` | optional | Digest cadence |
| `TELEGRAPH_SHORT_NAME`, `TELEGRAPH_AUTHOR_NAME` | optional | Branding for Telegraph digests |

### VPS SSH Secrets (for GitHub Actions)
- `VPS_HOST`
- `VPS_USERNAME`
- `VPS_PORT` (default `22`)
- `VPS_PATH` (default `~/codenews`)
- `VPS_SSH_KEY` (private key used by Actions to SSH into the server)

## 3. GitHub Actions → Docker → VPS
1. Push your code to `main` (or trigger the workflow manually).
2. Workflow steps:
   - Build Docker image.
   - Push to GitHub Container Registry (`ghcr.io/<user>/<repo>:latest`).
   - SSH into the VPS, pull the latest image, and restart `docker compose`.
3. Ensure repository permissions: *Settings → Actions → General → Workflow permissions → Read & write*.
4. Optional: make the container image public under *Packages → <image> → Change visibility*.

## 4. Manual VPS Deployment
```bash
# Install Docker on Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Prepare app directory
mkdir -p ~/codenews && cd ~/codenews

# Copy repo or pull from Git
git clone https://github.com/<you>/codenews.git .

# Add your .env file
nano .env

# Launch
docker compose pull   # optional if using GHCR
docker compose up -d

# Logs
docker compose logs -f
```

## 5. Verifying The Deployment
- `docker compose ps` → container is running.
- `docker compose logs --tail=100 codenews` → check for Telegram/startup errors.
- Use `/trg` in Telegram to force a scan and verify notifications.
- Use `/blog` to ensure Telegraph publishing works (should return a URL).

## 6. Troubleshooting
- **Permission denied while pushing image** → grant Actions write access to packages or adjust workflow permissions in `.github/workflows/`.
- **SSH failures** → confirm `VPS_SSH_KEY` matches `~/.ssh/authorized_keys` on the server and that `VPS_PORT` is exposed.
- **Container restarts** → run `docker compose logs codenews` to inspect stack traces (missing env vars, invalid Telegram token, etc.).
- **No digests generated** → ensure enough positive feedback exists (`BLOG_MIN_ITEMS`) and that OpenAI credentials are present if you rely on AI-generated summaries.

## 7. Keeping Runtime Config Flexible
- Inject overrides via env vars rather than editing `config.yaml` in production. Examples:
  ```bash
  RSS_CHECK_INTERVAL_HOURS=1 \
  BLOG_MIN_ITEMS=8 \
  KEYWORDS="ai,ml,devops,security" \
  docker compose up -d
  ```
- The same values can be defined as GitHub Secrets so CI/CD and local runs stay in sync.

## 8. Security Checklist
- Rotate Telegram/OpenAI tokens regularly.
- Restrict SSH keys to the deployment host.
- Keep Docker and system packages up to date (`apt update && apt upgrade`).
- Never commit `.env` or secrets to the repository.

Happy shipping! 🛳️
