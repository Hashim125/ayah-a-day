"""Quran dataset loading, validation, sanitization, and read-only access."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import nh3

import config

VERSE_KEY_RE = re.compile(r"^(\d{1,3}):(\d{1,3})$")
EXPECTED_VERSE_COUNT = 6236
SURAH_NAMES = (
    "Al-Fatihah", "Al-Baqarah", "Ali 'Imran", "An-Nisa", "Al-Ma'idah", "Al-An'am",
    "Al-A'raf", "Al-Anfal", "At-Tawbah", "Yunus", "Hud", "Yusuf", "Ar-Ra'd",
    "Ibrahim", "Al-Hijr", "An-Nahl", "Al-Isra", "Al-Kahf", "Maryam", "Ta-Ha",
    "Al-Anbiya", "Al-Hajj", "Al-Mu'minun", "An-Nur", "Al-Furqan", "Ash-Shu'ara",
    "An-Naml", "Al-Qasas", "Al-'Ankabut", "Ar-Rum", "Luqman", "As-Sajdah",
    "Al-Ahzab", "Saba", "Fatir", "Ya-Sin", "As-Saffat", "Sad", "Az-Zumar",
    "Ghafir", "Fussilat", "Ash-Shura", "Az-Zukhruf", "Ad-Dukhan", "Al-Jathiyah",
    "Al-Ahqaf", "Muhammad", "Al-Fath", "Al-Hujurat", "Qaf", "Adh-Dhariyat",
    "At-Tur", "An-Najm", "Al-Qamar", "Ar-Rahman", "Al-Waqi'ah", "Al-Hadid",
    "Al-Mujadilah", "Al-Hashr", "Al-Mumtahanah", "As-Saff", "Al-Jumu'ah",
    "Al-Munafiqun", "At-Taghabun", "At-Talaq", "At-Tahrim", "Al-Mulk", "Al-Qalam",
    "Al-Haqqah", "Al-Ma'arij", "Nuh", "Al-Jinn", "Al-Muzzammil", "Al-Muddaththir",
    "Al-Qiyamah", "Al-Insan", "Al-Mursalat", "An-Naba", "An-Nazi'at", "'Abasa",
    "At-Takwir", "Al-Infitar", "Al-Mutaffifin", "Al-Inshiqaq", "Al-Buruj", "At-Tariq",
    "Al-A'la", "Al-Ghashiyah", "Al-Fajr", "Al-Balad", "Ash-Shams", "Al-Layl",
    "Ad-Duha", "Ash-Sharh", "At-Tin", "Al-'Alaq", "Al-Qadr", "Al-Bayyinah",
    "Az-Zalzalah", "Al-'Adiyat", "Al-Qari'ah", "At-Takathur", "Al-'Asr", "Al-Humazah",
    "Al-Fil", "Quraysh", "Al-Ma'un", "Al-Kawthar", "Al-Kafirun", "An-Nasr",
    "Al-Masad", "Al-Ikhlas", "Al-Falaq", "An-Nas",
)
SURAH_AYAH_COUNTS = (
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128,
    111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73,
    54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60,
    49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52,
    44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19,
    26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7,
    3, 6, 3, 5, 4, 5, 6,
)
ALLOWED_TAFSIR_TAGS = {"p", "h2", "div", "em", "strong", "b", "i", "br", "ul", "ol", "li"}
ALLOWED_TAFSIR_ATTRIBUTES = {"p": {"lang", "dir"}, "div": {"lang", "dir"}}


class DataIntegrityError(RuntimeError):
    """Raised when a Quran dataset fails integrity checks."""


@dataclass(frozen=True, slots=True)
class Verse:
    verse_key: str
    surah: int
    ayah: int
    surah_name: str
    quran_text: str
    translation_text: str
    tafsir_html: str
    tafsir_plain: str


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataIntegrityError(f"Could not load {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise DataIntegrityError(f"{path.name} must contain a JSON object")
    return value


def sanitize_tafsir(html: str) -> str:
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=ALLOWED_TAFSIR_TAGS,
        attributes=ALLOWED_TAFSIR_ATTRIBUTES,
        clean_content_tags={"script", "style", "template", "iframe", "object"},
        strip_comments=True,
    )


def html_to_plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


class QuranRepository:
    """Validated, immutable Quran content repository."""

    def __init__(self, verses: Mapping[str, Verse]):
        self._verses = MappingProxyType(dict(verses))
        self._keys = tuple(verses)

    @classmethod
    def load(cls) -> "QuranRepository":
        valid, message = config.validate_data_directory()
        if not valid:
            raise DataIntegrityError(message)
        return cls.from_sources(
            _load_json(config.get_data_file_path("quran")),
            _load_json(config.get_data_file_path("translation")),
            _load_json(config.get_data_file_path("tafsir")),
            require_complete=True,
        )

    @classmethod
    def from_sources(cls, quran: Mapping[str, Any], translations: Mapping[str, Any],
                     tafsir: Mapping[str, Any], *, require_complete: bool = False) -> "QuranRepository":
        keys = (set(quran), set(translations), set(tafsir))
        if not (keys[0] == keys[1] == keys[2]):
            raise DataIntegrityError("Quran, translation, and Tafsir key sets differ")
        if require_complete and len(quran) != EXPECTED_VERSE_COUNT:
            raise DataIntegrityError(f"Expected {EXPECTED_VERSE_COUNT} verses, found {len(quran)}")

        resolved: dict[str, str] = {}
        sanitized: dict[str, tuple[str, str]] = {}

        def resolve(key: str, trail: tuple[str, ...] = ()) -> str:
            if key in resolved:
                return resolved[key]
            if key in trail:
                raise DataIntegrityError(f"Cyclic Tafsir reference: {' -> '.join((*trail, key))}")
            if len(trail) >= config.MAX_TAFSIR_REFERENCE_DEPTH:
                raise DataIntegrityError(f"Tafsir reference chain too deep at {key}")
            entry = tafsir.get(key)
            if isinstance(entry, dict):
                raw = entry.get("text", "")
            elif isinstance(entry, str) and VERSE_KEY_RE.fullmatch(entry.strip()):
                target = entry.strip()
                if target not in tafsir:
                    raise DataIntegrityError(f"Missing Tafsir reference {target} from {key}")
                raw = resolve(target, (*trail, key))
            elif isinstance(entry, str):
                raw = entry
            else:
                raise DataIntegrityError(f"Invalid Tafsir entry for {key}")
            if not isinstance(raw, str):
                raise DataIntegrityError(f"Invalid Tafsir text for {key}")
            resolved[key] = raw
            return raw

        verses: dict[str, Verse] = {}
        ordered = sorted(quran, key=lambda key: tuple(map(int, key.split(":"))))
        for key in ordered:
            match = VERSE_KEY_RE.fullmatch(key)
            if not match:
                raise DataIntegrityError(f"Invalid verse key: {key}")
            surah, ayah = map(int, match.groups())
            if not 1 <= surah <= 114 or not 1 <= ayah <= SURAH_AYAH_COUNTS[surah - 1]:
                raise DataIntegrityError(f"Invalid verse reference: {key}")
            q_entry = quran[key]
            if not isinstance(q_entry, dict) or q_entry.get("surah") != surah or q_entry.get("ayah") != ayah:
                raise DataIntegrityError(f"Quran metadata does not match {key}")
            arabic = q_entry.get("text")
            if not isinstance(arabic, str) or not arabic.strip():
                raise DataIntegrityError(f"Missing Quran text for {key}")
            t_entry = translations[key]
            translation = t_entry.get("t", "") if isinstance(t_entry, dict) else t_entry
            if not isinstance(translation, str) or not translation.strip():
                raise DataIntegrityError(f"Missing translation for {key}")
            raw_tafsir = resolve(key)
            cached_tafsir = sanitized.get(raw_tafsir)
            if cached_tafsir is None:
                tafsir_html = sanitize_tafsir(raw_tafsir)
                cached_tafsir = (tafsir_html, html_to_plain_text(tafsir_html))
                sanitized[raw_tafsir] = cached_tafsir
            tafsir_html, tafsir_plain = cached_tafsir
            verses[key] = Verse(key, surah, ayah, SURAH_NAMES[surah - 1], arabic,
                                translation, tafsir_html, tafsir_plain)
        return cls(verses)

    def __len__(self) -> int:
        return len(self._verses)

    @property
    def keys(self) -> tuple[str, ...]:
        return self._keys

    @property
    def verses(self) -> tuple[Verse, ...]:
        return tuple(self._verses.values())

    def get(self, verse_key: str) -> Verse | None:
        return self._verses.get(verse_key)

    def neighbors(self, verse: Verse, radius: int = 2) -> tuple[list[Verse], list[Verse]]:
        before = [self._verses[f"{verse.surah}:{n}"] for n in range(max(1, verse.ayah - radius), verse.ayah)]
        last = SURAH_AYAH_COUNTS[verse.surah - 1]
        after = [self._verses[f"{verse.surah}:{n}"] for n in range(verse.ayah + 1, min(last, verse.ayah + radius) + 1)]
        return before, after

    def previous_key(self, verse: Verse) -> str | None:
        return f"{verse.surah}:{verse.ayah - 1}" if verse.ayah > 1 else None

    def next_key(self, verse: Verse) -> str | None:
        return f"{verse.surah}:{verse.ayah + 1}" if verse.ayah < SURAH_AYAH_COUNTS[verse.surah - 1] else None
