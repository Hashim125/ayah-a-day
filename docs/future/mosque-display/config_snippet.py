# Removed from config.py (placed after PUBLIC_BASE_URL).
# Optional mosque display (/display) settings, set by the operator.
MOSQUE_NAME = os.getenv("MOSQUE_NAME", "").strip()[:80]
MOSQUE_NOTICE = os.getenv("MOSQUE_NOTICE", "").strip()[:240]
try:
    # Days to add to the Umm al-Qura Hijri date to match local moon sighting.
    HIJRI_OFFSET_DAYS = max(-2, min(2, int(os.getenv("HIJRI_OFFSET_DAYS", "0"))))
except ValueError:
    HIJRI_OFFSET_DAYS = 0
