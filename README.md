# GapGuard — Telegram Group Moderation Bot

> GapGuard is a modular, SQL-backed Telegram moderation bot designed to help group admins manage communities at scale. It provides configurable moderation tools (ban/kick/mute/warn), automated filters (word filter, anti-link, anti-forward), action logging, and an extensible architecture for adding anti-spam and custom UX features.

## Key Features

- Moderation: `/ban`, `/unban`, `/kick`, `/mute`, `/unmute`, `/warn`, `/unwarn` and configurable auto-actions on reaching warn thresholds.
- Filters: persistent banned words, auto-delete on match, anti-link and anti-forward protections.
- Persistent Storage: SQLite + SQLAlchemy models for chat settings, warns, logs, special members, tags, and banned words.
- Action Logging: Records administrative actions and automatic moderation decisions to a `logs` table for auditing and reporting.
- Extensible: Modular `groups/` handlers for focused responsibilities and easy additions (anti-spam, welcome/goodbye, inline menus).

## Repo Structure

- `main.py` — bot bootstrap, handler registration, and DB initialization.
- `db.py` — SQLAlchemy engine, `SessionLocal`, and declarative base (supports `DATABASE_URL` override from `.env`).
- `models.py` — ORM models (`ChatSetting`, `Warn`, `Log`, `SpecialMember`, `Tag`, `BannedWord`).
- `groups/` — command and message handlers, one module per feature:
  - `ban.py`, `unban.py`, `kick.py`, `mute.py`, `unmute.py` — member management.
  - `warn.py` — warn system with per-chat thresholds.
  - `filter.py` — banned words, anti-link, anti-forward.
  - `settings.py` — per-chat settings commands and shared setting accessors.
  - `roles.py`, `messages.py`, `logs.py` — special members/tags/promote, delete/purge, action logs.
- `utils/helpers.py` — shared helper functions (admin checks, mention formatting, extraction helpers).
- `utils/guards.py` — shared command guards and message/error templates used by all handlers.
- `data/` — local SQLite database (created at runtime).
- `requirements.txt` — pinned Python dependencies.

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

On startup the bot will create the required SQLite tables defined in `models.py`.

## Configuration

- Chat-level settings are stored in the `ChatSetting` model. Features can be toggled per-group and persisted across restarts.
- Extend or change default behavior by editing handlers in `groups/` and the ORM schemas in `models.py`.

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