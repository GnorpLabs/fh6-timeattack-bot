import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")

DB_PATH: Path = Path(os.getenv("DB_PATH", "data/timeattack.db"))
SCREENSHOTS_DIR: Path = Path(os.getenv("SCREENSHOTS_DIR", "screenshots"))
API_PORT: int = int(os.getenv("API_PORT", "8080"))

# Each tuple: (group label shown in autocomplete, list of track names)
TRACK_GROUPS: list[tuple[str, list[str]]] = [
    ("Road Racing · Circuits", [
        "Highway Circuit",
        "Narai-Juku Circuit",
        "Shirakawa Circuit",
        "Shimanoyama Circuit",
        "Hokubu Circuit",
        "Soni Circuit",
        "Daikoku Circuit",
        "Electric Town Circuit",
        "Legend Island Circuit",
        "Irokawa Circuit",
    ]),
    ("Road Racing · Sprints", [
        "Festival Sprint",
        "Venus Sprint",
        "Seaside Park Sprint",
        "Ito Sprint",
        "Tateyama Kurobe Sprint",
        "Shimanoyama Sprint",
        "Satta Sprint",
        "Coastline Sprint",
        "Tokyo Railway Sprint",
        "Shikisai Sprint",
    ]),
    ("Road Racing · Finale", [
        "The Colossus",
        "The Goliath",
    ]),
    ("Dirt Racing · Scrambles", [
        "Chiheisen Scramble",
        "Sotoyama Scramble",
        "Hirosaki Scramble",
        "Sunflower Scramble",
        "Bamboo Forest Scramble",
        "Ine Scramble",
        "Horizon Stadium Scramble",
        "Taiyaki Scramble",
        "Kawazu Nanadaru Scramble",
        "Sekibe Scramble",
    ]),
    ("Dirt Racing · Trails", [
        "Nukabira Trail",
        "Waterfall Trail",
        "Hokubu Trail",
        "Ito Trail",
        "Airfield Trail",
        "Cherry Field Trail",
        "Kinkaku-ji Trail",
        "Legend Island Trail",
        "Oyashirazu Trail",
        "Takashiro Trail",
    ]),
    ("Dirt Racing · Finale", [
        "The Gauntlet",
    ]),
    ("Cross Country · Circuits", [
        "Legend Island Cross Country Circuit",
        "Naruo Cross Country Circuit",
        "Snow Forest Cross Country Circuit",
        "Oka Cross Country Circuit",
        "Edogawa Cross Country Circuit",
        "City Docks Cross Country Circuit",
        "Stadium Cross Country Circuit",
        "Nangan Cross Country Circuit",
    ]),
    ("Cross Country · Point-to-Point", [
        "Soni Highlands Cross Country",
        "Ruriko-ji Cross Country",
        "Takashiro Cross Country",
        "Tateyama Alpine Cross Country",
        "Wind Farm Cross Country",
        "Yahikoyama Cross Country",
        "Shimanoyama Cross Country",
        "Shinjuku Gyoen Cross Country",
        "Temple Cross Country",
        "Izu Cross Country",
    ]),
    ("Cross Country · Finale", [
        "The Titan",
    ]),
    ("Street Racing", [
        "Daikoku Chase",
        "Norikura Descent",
        "Nachi Run",
        "Hokubu Ascent",
        "Okishinaimura Run",
        "Sunflower Charge",
        "Kita Ine",
        "Rainbow Bridge Descent",
        "Shimanoyama Charge",
        "Festival Chase",
        "Matsumi Climb",
        "Minami Chase",
        "River Descent",
        "Cedar Run",
        "Tokyo City Docks Charge",
    ]),
    ("Drag Racing", [
        "Horizon Festival Drag Strip",
        "Pop-up Drag Meets",
    ]),
    ("Touge Battles", [
        "Hakone Nanamagari",
        "Mt Haruna",
        "Norikura Skyline",
        "Arashiyama Takao",
        "Bandai Azuma",
    ]),
    ("Time Attacks", [
        "Sekibe Time Attack",
        "Pop-up Time Attack Circuits",
    ]),
]

# Flat set of all valid track names — used for validation
TRACKS: set[str] = {track for _, tracks in TRACK_GROUPS for track in tracks}

CLASSES: list[str] = ["D", "C", "B", "A", "S1", "S2", "R", "X"]

VEHICLES: list[dict] = []


def get_vehicle_names() -> list[str]:
    return [v["name"] for v in VEHICLES]
