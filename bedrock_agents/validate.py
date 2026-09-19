"""Last line of defence before a meeting's output goes live on the public Bedrock page.

Bad text fields are dropped (the page keeps its previous text for that field); a bad image is
rejected (the page keeps its previous hero). Nothing here raises: it reports problems instead.
"""
import os
import re

TITLE_KEYS = {"strategy_title", "risk_title", "opp_title", "insight_title"}
TEXT_KEYS = {"strategy_desc", "risk_desc", "opp_desc", "insight_desc"}
TILE_KEYS = {"market_inflation", "market_risk", "market_yield", "market_sector", "market_sp500",
             "market_volatility", "market_outlook"}
MAX_LEN = {**{k: 80 for k in TITLE_KEYS}, **{k: 400 for k in TEXT_KEYS}, **{k: 40 for k in TILE_KEYS}}

# Things that should never appear in copy we publish.
_BAD_TEXT = re.compile(r"<|>|```|===|https?://|\{\{|\}\}", re.IGNORECASE)
_TILE_OK = re.compile(r"^[\w\s.,%$+\-()▲▼▬—/]+$")
HERO_PATH = re.compile(r"^/assets/bedrock_\d{8}-\d{4}\.png$")

MIN_IMAGE_BYTES = 100_000
MIN_COARSE_CONTRAST = 20.0  # measured 2026-09-19: noise renders 2-12, real scenes 60-80


def validate_updates(updates):
    """Returns (clean_updates, problems). Unknown keys are dropped; bad fields are removed."""
    clean, problems = {}, []
    for key, value in (updates or {}).items():
        if key == "hero_image":
            continue  # validated separately by check_image()
        if key not in MAX_LEN:
            problems.append(f"{key}: unknown field dropped")
            continue
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{key}: empty")
            continue
        text = " ".join(value.split())
        if len(text) > MAX_LEN[key]:
            problems.append(f"{key}: too long ({len(text)} > {MAX_LEN[key]})")
            continue
        if _BAD_TEXT.search(text):
            problems.append(f"{key}: contains markup or a link")
            continue
        if key in TILE_KEYS and not _TILE_OK.match(text):
            problems.append(f"{key}: unexpected characters")
            continue
        clean[key] = text
    return clean, problems


def coarse_contrast(path):
    """Standard deviation of a tiny grayscale thumbnail. Flat texture/noise scores low."""
    from PIL import Image
    with Image.open(path) as im:
        small = im.convert("L").resize((32, 18))
    px = list(small.getdata())
    mean = sum(px) / len(px)
    return (sum((p - mean) ** 2 for p in px) / len(px)) ** 0.5


def check_image(path, min_bytes=MIN_IMAGE_BYTES):
    """Returns (ok, reason). Real PNG, big enough, decodes, and is not flat texture/noise."""
    try:
        if not os.path.isfile(path):
            return False, "file missing"
        size = os.path.getsize(path)
        if size < min_bytes:
            return False, f"too small ({size} bytes)"
        with open(path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return False, "not a PNG"
        try:
            contrast = coarse_contrast(path)
        except ImportError:
            return True, "ok (no Pillow: content check skipped)"
        if contrast < MIN_COARSE_CONTRAST:
            return False, f"looks like flat texture/noise (contrast {contrast:.1f})"
        return True, f"ok (contrast {contrast:.1f})"
    except Exception as e:
        return False, f"unreadable: {e}"


def valid_hero_path(image_path):
    return bool(image_path and HERO_PATH.match(image_path))
