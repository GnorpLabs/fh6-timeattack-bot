import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")

DB_PATH: Path = Path(os.getenv("DB_PATH", "data/timeattack.db"))
SCREENSHOTS_DIR: Path = Path(os.getenv("SCREENSHOTS_DIR", "screenshots"))

TRACKS: list[str] = [
    # Replace with actual FH6 time attack track names
    "Horizon Circuit",
    "Goliath",
    "Colossus",
    "Gauntlet",
    "Marathon",
]

CLASSES: list[str] = ["D", "C", "B", "A", "S1", "S2", "X"]

VEHICLES: list[dict] = []


def get_vehicle_names() -> list[str]:
    return [v["name"] for v in VEHICLES]
