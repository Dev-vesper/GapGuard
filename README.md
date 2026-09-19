<div align="center">

# GapGuard

GapGuard is a Telegram group moderation bot built for Persian-speaking communities.
It handles bans, kicks, mutes and warns, filters banned words, links and forwarded messages,
locks selected content types, and records every administrative action in an auditable log.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![pyTelegramBotAPI](https://img.shields.io/badge/pyTelegramBotAPI-4.x-2CA5E0?logo=telegram&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![python-dotenv](https://img.shields.io/badge/python--dotenv-.env-ECD53F)
![License](https://img.shields.io/badge/License-BSD%202--Clause-4C4C4C)

</div>

## Requirements

- Python 3.10 or newer
- Git
- A bot token from [@BotFather](https://t.me/BotFather)

## Running the bot

Running the bot inside a virtual environment is recommended on every operating system — it keeps the
project dependencies isolated from your global Python installation and makes the setup reproducible.

### Linux / macOS

```bash
git clone <your-repo-url>
cd GapGuard

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# open .env and set BOT_TOKEN to the token you got from BotFather

python main.py
```

### Windows

PowerShell:

```powershell
git clone <your-repo-url>
cd GapGuard

py -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

copy .env.example .env
# open .env and set BOT_TOKEN to the token you got from BotFather

python main.py
```

Command Prompt (`cmd.exe`) — same steps, only the activation line differs:

```bat
git clone <your-repo-url>
cd GapGuard

py -m venv .venv
.\.venv\Scripts\activate.bat

pip install -r requirements.txt

copy .env.example .env
python main.py
```

### Notes

- If PowerShell refuses to run the activation script, allow it for the current session only:

  ```powershell
  Set-ExecutionPolicy -Scope Process -RemoteSigned
  ```

- When the virtual environment is active, plain `python` and `pip` already point inside `.venv` — no
  global install is needed. Run `deactivate` to leave it.
- The `data/` directory and the SQLite database file are created automatically on the first start.
- The same steps work on any other Unix-like system (for example WSL, which follows the Linux path).

## License

BSD 2-Clause License — see [LICENSE](LICENSE) for details.
