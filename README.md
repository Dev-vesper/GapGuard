# GapGuard — Telegram Group Moderation Bot

> GapGuard is a modular, SQL-backed Telegram moderation bot designed to help group admins manage communities at scale. It provides configurable moderation tools (ban/kick/mute/warn), automated filters (word filter, anti-link, anti-forward), action logging, and an extensible architecture for adding anti-spam and custom UX features.

## Key Features

- Moderation: `/ban`, `/unban`, `/kick`, `/mute`, `/unmute`, `/warn`, `/unwarn` and configurable auto-actions on reaching warn thresholds.
- Filters: persistent banned words, auto-delete on match, anti-link and anti-forward protections.
- Persistent Storage: SQLite + SQLAlchemy models for chat settings, warns, logs, special members, tags, banned words, content restrictions, and message statistics.
- Action Logging: Records administrative actions and automatic moderation decisions to a `logs` table for auditing and reporting.
- Extensible: A layered architecture (`core` → `database` → `services` → `bot`) with one handler module per feature, so new commands only need a thin handler plus a service function.

## Repo Structure

- `main.py` — bot bootstrap, handler registration, and DB initialization.
- `core/` — infrastructure shared by every layer:
  - `config.py` — `.env` loading, `BOT_TOKEN`/`DATABASE_URL` resolution, and the repo-root `data/` path.
  - `database.py` — SQLAlchemy engine, `SessionLocal`, `Base`, and the `session_scope()` transaction boundary.
  - `logger.py` — `setup_logging()` and `get_logger()`.
- `database/` — data access layer:
  - `models.py` — ORM models (`ChatSetting`, `Warn`, `Log`, `SpecialMember`, `Tag`, `BannedWord`, `ContentRestriction`, `MessageStat`).
  - `repositories.py` — every CRUD query in one place; each function receives a `Session` as its first argument and never opens one.
- `services/` — business logic and transaction boundaries: `moderation_service.py`, `filter_service.py`, `settings_service.py`, `stats_service.py`, `restrict_service.py`, `roles_service.py`, `log_service.py`.
- `bot/` — presentation layer:
  - `loader.py` — auto-discovers `<name>_handler(bot)` functions in `bot/handlers/` and registers them in `PRIORITY_MAP` order (the catch-all filter module must stay last).
  - `guards.py` — command/target guards plus shared report and error templates.
  - `helpers.py` — pure helpers (group check, HTML escaping, mention building, target extraction).
  - `handlers/` — one module per feature: `moderation.py`, `filter.py`, `logs.py`, `settings.py`, `stats.py`, `restrict.py`, `roles.py`, `messages.py`.
- `data/` — local SQLite database (created at runtime).
- `requirements.txt` — pinned Python dependencies.

Handlers parse the message, run guards, call a service, and format the Persian reply — they never touch a `Session` or a model directly. Services own the business rules and the Telegram API calls; repositories own the SQL.

## Requirements

- Python 3.10+ recommended
- Dependencies (install via pip): listed in `requirements.txt`

## Quick Start

1. Clone the repository:

```bash
git clone <your-repo-url>
cd GapGuard
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (PowerShell)
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your bot token (example):

```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=sqlite:///data/gapguard.db
```

5. Run the bot:

```bash
python main.py
```

On startup the bot will create the required SQLite tables defined in `database/models.py`.

## Configuration

- Chat-level settings are stored in the `ChatSetting` model. Features can be toggled per-group and persisted across restarts.
- Extend or change default behavior by editing handlers in `bot/handlers/` and the ORM schemas in `database/models.py`.

## Development Notes

- Database: The project uses SQLAlchemy Core/ORM directly. For production migrations, integrate Alembic.
- Testing: Add unit tests for each handler and DB operation. Consider using a temporary SQLite database or an in-memory DB for CI.
- Error Handling: Centralize Telegram API exception handling around send/restrict ops to improve resilience in large groups.

## Contributing

1. Fork the repository and create a feature branch.
2. Run tests and linters locally.
3. Open a PR with a clear description of the change.

Please follow conventional commit messaging for clearer history.

## Roadmap

- Anti-spam module (rate-limiting, repeated message detection)
- Welcome/goodbye message system with per-chat templates
- Admin UI via inline keyboards and paginated lists
- Exportable logs and reporting endpoints