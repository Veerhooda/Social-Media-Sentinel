from __future__ import annotations

import os
from pathlib import Path

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from app.core.config import Settings

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def save_session_string(session_string: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    replacement = f"TELEGRAM_SESSION_STRING={session_string}"
    output: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("TELEGRAM_SESSION_STRING="):
            output.append(replacement)
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.extend(["", replacement])

    temporary = ENV_PATH.with_name(".env.telegram-session.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("\n".join(output) + "\n")
    temporary.replace(ENV_PATH)
    ENV_PATH.chmod(0o600)


def main() -> int:
    settings = Settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        print("Telegram API ID/hash are not configured in .env.")
        return 2

    print("Authorize the Telegram account for public-channel collection.")
    print("The resulting session string will be saved directly to .env and not displayed.")
    with TelegramClient(
        StringSession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    ) as client:
        session_string = client.session.save()
    if not session_string:
        print("Telegram did not return an authorized session string.")
        return 3
    save_session_string(session_string)
    print("Telegram session saved securely to .env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
