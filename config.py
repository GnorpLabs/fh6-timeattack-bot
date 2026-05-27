import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")

DB_PATH: Path = Path(os.getenv("DB_PATH", "data/timeattack.db"))
SCREENSHOTS_DIR: Path = Path(os.getenv("SCREENSHOTS_DIR", "screenshots"))
API_PORT: int = int(os.getenv("API_PORT", "8080"))

TRACKS: list[str] = [
    "Legend island",
    "Hokubu Circuit",
    "Soni Circuit",
    "Sekibe Circuit",
]

CLASSES: list[str] = ["D", "C", "B", "A", "S1", "S2", "R", "X"]

VEHICLES: list[dict] = []


def get_vehicle_names() -> list[str]:
    return [v["name"] for v in VEHICLES]
