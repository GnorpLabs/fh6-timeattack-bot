import json
import os
from pathlib import Path

if "APPDATA" in os.environ:
    CONFIG_DIR: Path = Path(os.environ["APPDATA"]) / "FH6BotRelay"
else:
    CONFIG_DIR = Path.home() / "FH6BotRelay"
CONFIG_FILE: Path = CONFIG_DIR / "config.json"

_REQUIRED_KEYS = ("token", "api_url", "discord_id", "discord_username")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)  # atomic on POSIX; near-atomic on Windows


def save_setup(api_url: str, discord_id: str, discord_username: str, token: str) -> None:
    cfg = load_config()
    cfg.update({
        "api_url": api_url,
        "discord_id": discord_id,
        "discord_username": discord_username,
        "token": token,
    })
    _save_raw(cfg)


def update_token(token: str) -> None:
    cfg = load_config()
    cfg["token"] = token
    _save_raw(cfg)


def is_setup_complete() -> bool:
    cfg = load_config()
    return all(k in cfg and cfg[k] for k in _REQUIRED_KEYS)


def get_udp_port() -> int:
    return load_config().get("udp_port", 20440)
