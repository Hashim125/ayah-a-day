"""Environment-driven configuration for Ayah App."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("AYAH_DATA_DIR", BASE_DIR / "data")).resolve()
STATIC_FOLDER = BASE_DIR / "static"
STATIC_ASSET_VERSION = "20260825d"
REQUIRED_FILES = {
    "quran": "qpc-hafs.json",
    "translation": "en-taqi-usmani-simple.json",
    "tafsir": "en-tafisr-ibn-kathir.json",
}
MAX_SEARCH_RESULTS = 20
MAX_API_PAGE_SIZE = 50
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 200
MAX_THEME_RESULTS = 25
MAX_TAFSIR_REFERENCE_DEPTH = 25
APP_NAME = "Ayah App"
APP_DESCRIPTION = "Daily Quranic verses with Taqi Usmani's translation and Ibn Kathir's commentary."
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Europe/London")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
DEBUG_MODE = os.getenv("DEBUG", "").lower() in {"1", "true", "yes", "on"}
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))


def get_data_file_path(file_key: str) -> Path:
    """Return an absolute path for a configured dataset."""
    try:
        filename = REQUIRED_FILES[file_key]
    except KeyError as exc:
        raise ValueError(f"Unknown data file key: {file_key}") from exc
    return DATA_DIR / filename


def validate_data_directory() -> tuple[bool, str]:
    """Check that the data directory and required datasets exist."""
    if not DATA_DIR.is_dir():
        return False, f"Data directory '{DATA_DIR}' not found"
    missing = [name for name in REQUIRED_FILES.values() if not (DATA_DIR / name).is_file()]
    if missing:
        return False, f"Missing required files: {', '.join(missing)}"
    return True, "All data files found"
