"""Configuration file for Ayah-a-Day application."""

import os

# Data Directory Configuration
DATA_DIR = 'data'

# Required Data Files
REQUIRED_FILES = {
    'quran': 'qpc-hafs.json',
    'translation': 'en-taqi-usmani-simple.json',
    'tafsir': 'en-tafisr-ibn-kathir.json'
}

# Search Configuration
MAX_SEARCH_RESULTS = 20
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 200
MAX_THEME_RESULTS = 25

# Tafsir Resolution Configuration
MAX_TAFSIR_REFERENCE_DEPTH = 3

# Theme Categories for Verse Search
VERSE_THEMES = {
    "Prayer & Worship": ["prayer", "worship", "salah", "prostrate", "bow", "kneel", "remembrance", "dhikr", "praise"],
    "Faith & Belief": ["believe", "faith", "trust", "iman", "believer", "faithful", "conviction", "certainty"],
    "Patience & Perseverance": ["patience", "persevere", "endure", "steadfast", "sabr", "persist", "bear"],
    "Forgiveness & Mercy": ["forgive", "mercy", "compassion", "pardon", "merciful", "forgiving", "rahma"],
    "Guidance & Wisdom": ["guide", "guidance", "wisdom", "knowledge", "light", "path", "straight", "hidayah"],
    "Paradise & Afterlife": ["paradise", "heaven", "afterlife", "resurrection", "judgment", "garden", "jannah"],
    "Charity & Giving": ["charity", "giving", "spend", "poor", "needy", "zakat", "alms", "generous"],
    "Justice & Righteousness": ["justice", "righteous", "fair", "equity", "just", "right", "good deed"],
    "Fear & Hope": ["fear", "hope", "afraid", "terror", "anticipate", "expect", "reverence"],
    "Family & Relationships": ["family", "parent", "child", "spouse", "marriage", "mother", "father"],
    "Struggle & Hardship": ["trial", "test", "hardship", "difficulty", "struggle", "adversity", "challenge"],
    "Gratitude & Thankfulness": ["grateful", "thank", "appreciation", "blessing", "favor", "thankful"]
}

# Application Metadata
APP_NAME = "Ayah App"
APP_DESCRIPTION = "Daily Quranic verses with translations and Tafsir commentary. Discover the beauty and wisdom of the Quran with verse of the day, random ayah generator, and powerful search."
APP_KEYWORDS = ["Quran", "Ayah", "Tafsir", "Ibn Kathir", "Islamic", "Verse of the Day", "Translation", "Taqi Usmani"]

# Social Media / SEO Configuration
DEFAULT_OG_IMAGE = "https://ayahapp.com/static/og-image.png"
DEFAULT_OG_URL = "https://ayahapp.com"

# Flask Configuration
DEBUG_MODE = True
HOST = '0.0.0.0'
PORT = 5000

# Static Files Configuration
STATIC_FOLDER = 'static'
MOSQUE_IMAGE_FILENAME = 'PXL_20250601_024336215.jpg'


def get_data_file_path(file_key):
    """Get the full path for a data file."""
    filename = REQUIRED_FILES.get(file_key)
    if not filename:
        raise ValueError(f"Unknown data file key: {file_key}")
    return os.path.join(DATA_DIR, filename)


def validate_data_directory():
    """Check if data directory and all required files exist."""
    if not os.path.exists(DATA_DIR):
        return False, f"Data directory '{DATA_DIR}' not found"

    missing_files = []
    for key, filename in REQUIRED_FILES.items():
        filepath = get_data_file_path(key)
        if not os.path.exists(filepath):
            missing_files.append(filename)

    if missing_files:
        return False, f"Missing required files: {', '.join(missing_files)}"

    return True, "All data files found"
