# 🚀 CodeNews Quickstart (English)

This guide gets you from zero to a working Telegram bot (and Telegraph digest) in minutes, then shows how to collaborate via GitHub Flow.

## 1. Local Development

### Prerequisites
- Python 3.11+
- `pip` and `virtualenv`
- A Telegram bot token + chat ID

### Steps
1. **Clone & install**
   ```bash
   git clone https://github.com/<you>/codenews.git
   cd codenews
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Create `.env`**
   ```bash
   cp .env.example .env  # if the template exists
   ```
   Fill in the essentials:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC
   TELEGRAM_CHAT_ID=123456789
   OPENAI_API_KEY=sk-...          # optional, enables LLM summaries
   TIMEZONE=Europe/Istanbul       # optional
   LOG_LEVEL=INFO                 # optional
   ```
   Any setting from `config.yaml` can be overridden via env vars (see `README.md` for the full table).
3. **Initialise the SQLite database**
   ```bash
   python -c "from src.database import init_db; init_db()"
   ```
4. **Run the bot**
   ```bash
   python src/main.py
   ```
   - `/trg` triggers an immediate RSS scan.
   - `/blog` publishes the weekly Telegraph digest on demand.

### Optional: Docker Compose
```bash
docker compose up --build -d
docker compose logs -f
```
Ensure your `.env` file is available to Docker (either by copying it next to `docker-compose.yaml` or using Compose `env_file` entries).

### Tests
Install the lightweight dev dependency and run the suite before pushing:
```bash
pip install pytest
pytest
```

## 2. Runtime Configuration Cheatsheet
- Override behaviour by exporting env vars or injecting them with your process manager.
- Examples:
  ```bash
  export RSS_CHECK_INTERVAL_HOURS=1
  export BLOG_MIN_ITEMS=8
  export KEYWORDS="ai,deep learning,devops,security"
  python src/main.py
  ```
- GitHub Actions / Docker Compose can reference the same variables, so you keep a single source of truth.

## 3. GitHub Flow For Contributions
1. Fork the repo and clone your fork.
2. Create a feature branch: `git checkout -b feature/<short-description>`.
3. Make changes + tests: `pytest`.
4. Commit with clear messages: `git commit -m "feat: add Telegraph digest publisher"`.
5. Push and open a Pull Request against `main`.
6. Fill in the PR checklist (tests, docs, Apache-2.0 confirmation).

> **Note:** All contributions are accepted under the Apache License 2.0. By opening a PR you confirm that your work—and the resulting project—can be licensed under Apache-2.0.

## 4. Need More?
- **Deployment tips** (GitHub Actions, VPS, SSH, secrets) → `DEPLOYMENT.md`.
- **Coding standards & PR checklist** → `CONTRIBUTING.md`.

Happy hacking! 🎉
