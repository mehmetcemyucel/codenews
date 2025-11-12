# CodeNews 🤖

A privacy-friendly RSS intelligence bot that filters AI and software development news, personalises Telegram notifications, and publishes weekly Telegraph digests. All runtime parameters can now be overridden through environment variables, making the project portable across laptops, containers, and CI runs.

## Features
- 📡 **Smart harvesting** – Hourly RSS checks with request throttling and keyword-based relevance scoring powered by a single `keywords` list.
- 🤖 **Personalised feed** – Feedback-driven ML engine that rescores content based on your 👍/👎 interactions.
- 💬 **Telegram bot** – Compact summaries, inline feedback buttons, feed management commands, and ad-hoc trigger jobs.
- 📝 **Weekly Telegram blog digest** – Curated Telegraph page perfect for sharing directly in Telegram channels.
- 🌍 **Runtime-first configuration** – Every operational parameter (thresholds, schedules, limits) can be injected via env vars for Docker, GitHub Actions, or local shells.
- 🛡️ **Open licensing** – Released under Apache 2.0 so individuals and teams can extend it freely.

## Architecture At A Glance
```
RSS Feeds → Content Filter → Preference Learner → Telegram Bot
                                 │
                                 └── Weekly Telegraph Digest (optional)
```

## Getting Started
The quickest path is documented in `QUICKSTART.md`. In short:

1. **Clone & install**
   ```bash
   git clone https://github.com/<you>/codenews.git
   cd codenews
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Create `.env`**
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC
   TELEGRAM_CHAT_ID=123456789
   OPENAI_API_KEY=sk-...        # optional for LLM summaries
   ```
3. **Initialise the DB**
   ```bash
   python -c "from src.database import init_db; init_db()"
   ```
4. **Run the bot**
   ```bash
   python src/main.py
   ```

Docker, GitHub Actions, and GitHub Flow examples—plus SSH deployment notes—live in `DEPLOYMENT.md` and `QUICKSTART.md`.

## Configuration & Environment Variables
- `config.yaml` holds sane defaults for local development.
- Every numeric, boolean, and list setting respects a runtime env override. This keeps containers stateless and enables GitHub Action secrets to control behaviour.

| Variable | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from [BotFather](https://core.telegram.org/bots). |
| `TELEGRAM_CHAT_ID` | ✅ | Chat/channel ID that will receive notifications. |
| `OPENAI_API_KEY` | optional | Enables LLM-based Turkish summaries and digest headlines. |
| `DATABASE_URL` | optional | Defaults to `sqlite:///data/codenews.db`; point to Postgres for production. |
| `TIMEZONE` | optional | Defaults to `Europe/Istanbul`. |
| `LOG_LEVEL` | optional | `INFO`, `DEBUG`, etc. |
| `RSS_CHECK_INTERVAL_HOURS`, `MAX_ITEMS_PER_FEED`, `REQUEST_TIMEOUT_SECONDS` | optional | Control the RSS harvester cadence. |
| `KEYWORDS` | optional | Comma-separated override for the unified keyword list. |
| `MAX_NOTIFICATIONS_PER_HOUR`, `SUMMARY_MAX_LENGTH`, `TRANSLATE_SUMMARIES_TO_TURKISH` | optional | Notification tuning knobs. |
| `MAX_ARTICLE_AGE_HOURS`, `NEWS_KEYWORDS` | optional | Freshness filters. |
| `INITIAL_RELEVANCE_THRESHOLD`, `LEARNING_RATE`, `MIN_FEEDBACK_COUNT` | optional | ML engine controls. |
| `BLOG_MIN_ITEMS`, `BLOG_MAX_ITEMS`, `BLOG_SCHEDULE_DAY/HOUR/MINUTE` | optional | Digest cadence. |
| `TELEGRAPH_SHORT_NAME`, `TELEGRAPH_AUTHOR_NAME` | optional | Branding for Telegraph posts. |

Any variable missing from the table still accepts env overrides—inspect `src/config.py` for the full list.

## Telegram Bot Essentials
- `/start`, `/help` – Show command reference.
- `/stats` – Content and feedback counters.
- `/trg` – Manually trigger RSS → notification pipeline.
- `/blog` – Publish a Telegraph digest and mark included stories as “used”.
- `/testblog` – Publish a digest without mutating story state (great for previews).
- `/feeds`, `/addfeed`, `/removefeed`, `/togglefeed` – Manage RSS sources. Category labels are now free-form (e.g., `ai`, `devops`, `security`).
- Inline buttons send feedback that continuously refines personalisation scores.

## Project Structure
```
.
├── src/
│   ├── blog_generator.py   # Telegraph digest builder
│   ├── content_filter.py   # Unified keyword scoring + summaries
│   ├── telegram_bot.py     # Bot handlers and feedback logic
│   └── ...
├── data/feeds.json         # RSS feed registry
├── QUICKSTART.md           # Local + GitHub Flow playbook
├── DEPLOYMENT.md           # Docker / CI / VPS deployment guide
├── CONTRIBUTING.md         # Contribution guidelines
├── LICENSE                 # Personal-use-only terms
└── requirements.txt
```

## Testing
Install the optional dev dependency first:
```bash
pip install pytest
pytest
```
Run the suite (or targeted modules) before opening a PR to keep GitHub Actions green.

## Contributing
Contributions are welcome under Apache 2.0. Review `CONTRIBUTING.md` for:

- Branch/PR workflow (GitHub Flow).
- Coding style expectations.
- Commit hygiene and review checklist.

## License
CodeNews is released under the [Apache License 2.0](LICENSE).
