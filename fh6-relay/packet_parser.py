import struct
from dataclasses import dataclass

# Byte offsets match the FH6 "car dash" sled telemetry format.
# Reference: docs/superpowers/specs/2026-05-26-data-out-design.md
PACKET_SIZE = 324

# Full field layout for diagnostic logging.
# Sled section (bytes 0-231): unchanged across FH4/FH5/FH6.
# Dash section (bytes 232+): FH6 timing fields are shifted +12 vs FH4 due to
# three new f32 fields inserted at 284-295 whose purpose is unconfirmed.
# All offsets and unknown-field names must be verified against live FH6 telemetry.
_FIELD_LAYOUT: list[tuple[str, str, int]] = [
    # Sled section
    ("IsRaceOn",            "<i", 0),
    ("TimestampMS",         "<I", 4),
    ("EngineMaxRpm",        "<f", 8),
    ("EngineIdleRpm",       "<f", 12),
    ("CurrentEngineRpm",    "<f", 16),
    ("AccelX",              "<f", 20),
    ("AccelY",              "<f", 24),
    ("AccelZ",              "<f", 28),
    ("VelocityX",           "<f", 32),
    ("VelocityY",           "<f", 36),
    ("VelocityZ",           "<f", 40),
    ("AngularVelX",         "<f", 44),
    ("AngularVelY",         "<f", 48),
    ("AngularVelZ",         "<f", 52),
    ("Yaw",                 "<f", 56),
    ("Pitch",               "<f", 60),
    ("Roll",                "<f", 64),
    ("SuspNormFL",          "<f", 68),
    ("SuspNormFR",          "<f", 72),
    ("SuspNormRL",          "<f", 76),
    ("SuspNormRR",          "<f", 80),
    ("TireSlipRatioFL",     "<f", 84),
    ("TireSlipRatioFR",     "<f", 88),
    ("TireSlipRatioRL",     "<f", 92),
    ("TireSlipRatioRR",     "<f", 96),
    ("WheelRotSpeedFL",     "<f", 100),
    ("WheelRotSpeedFR",     "<f", 104),
    ("WheelRotSpeedRL",     "<f", 108),
    ("WheelRotSpeedRR",     "<f", 112),
    ("WheelOnRumbleFL",     "<i", 116),
    ("WheelOnRumbleFR",     "<i", 120),
    ("WheelOnRumbleRL",     "<i", 124),
    ("WheelOnRumbleRR",     "<i", 128),
    ("PuddleDepthFL",       "<f", 132),
    ("PuddleDepthFR",       "<f", 136),
    ("PuddleDepthRL",       "<f", 140),
    ("PuddleDepthRR",       "<f", 144),
    ("SurfaceRumbleFL",     "<f", 148),
    ("SurfaceRumbleFR",     "<f", 152),
    ("SurfaceRumbleRL",     "<f", 156),
    ("SurfaceRumbleRR",     "<f", 160),
    ("TireSlipAngleFL",     "<f", 164),
    ("TireSlipAngleFR",     "<f", 168),
    ("TireSlipAngleRL",     "<f", 172),
    ("TireSlipAngleRR",     "<f", 176),
    ("TireCombinedSlipFL",  "<f", 180),
    ("TireCombinedSlipFR",  "<f", 184),
    ("TireCombinedSlipRL",  "<f", 188),
    ("TireCombinedSlipRR",  "<f", 192),
    ("SuspTravelMetersFL",  "<f", 196),
    ("SuspTravelMetersFR",  "<f", 200),
    ("SuspTravelMetersRL",  "<f", 204),
    ("SuspTravelMetersRR",  "<f", 208),
    ("CarOrdinal",          "<i", 212),
    ("CarClass",            "<i", 216),
    ("CarPI",               "<i", 220),
    ("DrivetrainType",      "<i", 224),
    ("NumCylinders",        "<i", 228),
    # Dash extension
    ("PositionX",           "<f", 232),
    ("PositionY",           "<f", 236),
    ("PositionZ",           "<f", 240),
    ("Speed",               "<f", 244),
    ("Power",               "<f", 248),
    ("Torque",              "<f", 252),
    ("TireTempFL",          "<f", 256),
    ("TireTempFR",          "<f", 260),
    ("TireTempRL",          "<f", 264),
    ("TireTempRR",          "<f", 268),
    ("Boost",               "<f", 272),
    ("Fuel",                "<f", 276),
    ("DistanceTraveled",    "<f", 280),
    # Unknown fields new in FH5/FH6 vs FH4 — names TBD from live data
    ("Unk_284",             "<f", 284),
    ("Unk_288",             "<f", 288),
    ("Unk_292",             "<f", 292),
    # Timing (FH6 offsets — +12 vs FH4)
    ("BestLap",             "<f", 296),
    ("LastLap",             "<f", 300),
    ("CurrentLap",          "<f", 304),
    ("CurrentRaceTime",     "<f", 308),
    ("LapNumber",           "<H", 312),
    ("RacePosition",        "<B", 314),
    ("Accel",               "<B", 315),
    ("Brake",               "<B", 316),
    ("Clutch",              "<B", 317),
    ("HandBrake",           "<B", 318),
    ("Gear",                "<B", 319),
    ("Steer",               "<b", 320),
    ("NormDrivingLine",     "<b", 321),
    ("NormAIBrakeDiff",     "<b", 322),
    ("Unk_323",             "<B", 323),
]


@dataclass
class FH6Packet:
    is_race_on: int
    car_ordinal: int
    car_class: int
    best_lap: float
    last_lap: float
    current_lap: float
    current_race_time: float
    lap_number: int
    race_position: int


def parse_packet(data: bytes) -> FH6Packet | None:
    if len(data) != PACKET_SIZE:
        return None
    return FH6Packet(
        is_race_on=struct.unpack_from("<i", data, 0)[0],
        car_ordinal=struct.unpack_from("<i", data, 212)[0],
        car_class=struct.unpack_from("<i", data, 216)[0],
        best_lap=struct.unpack_from("<f", data, 296)[0],
        last_lap=struct.unpack_from("<f", data, 300)[0],
        current_lap=struct.unpack_from("<f", data, 304)[0],
        current_race_time=struct.unpack_from("<f", data, 308)[0],
        lap_number=struct.unpack_from("<H", data, 312)[0],
        race_position=struct.unpack_from("<B", data, 314)[0],
    )


def parse_all_fields(data: bytes) -> dict:
    """Decode every byte in the 324-byte FH6 packet for diagnostic logging.

    Unk_284/Unk_288/Unk_292 are three f32 fields new in FH5/FH6 vs FH4 that
    pushed the timing block forward by 12 bytes.  Their names are unknown until
    confirmed against live FH6 telemetry.
    """
    if len(data) != PACKET_SIZE:
        return {}
    return {
        name: struct.unpack_from(fmt, data, offset)[0]
        for name, fmt, offset in _FIELD_LAYOUT
    }
