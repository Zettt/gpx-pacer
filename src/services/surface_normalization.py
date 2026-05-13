"""Normalize OSM surface tags into the existing user-facing labels."""

_SURFACE_MAP: dict[str, str] = {
    "asphalt": "Asphalt",
    "paved": "Paved",
    "concrete": "Paved",
    "concrete:plates": "Paved",
    "concrete:lanes": "Paved",
    "paving_stones": "Paved",
    "sett": "Paved",
    "cobblestone": "Paved",
    "gravel": "Gravel",
    "fine_gravel": "Gravel",
    "pebblestone": "Gravel",
    "dirt": "Unpaved",
    "earth": "Unpaved",
    "ground": "Unpaved",
    "mud": "Unpaved",
    "sand": "Unpaved",
    "grass": "Unpaved",
    "compacted": "Compacted",
    "wood": "Wood",
    "metal": "Metal",
}


def normalize_surface(raw: str | None) -> str:
    """Map an OSM surface tag value to the existing user-facing label set."""
    if not raw:
        return "Unknown"
    return _SURFACE_MAP.get(raw.lower(), "Unknown")
