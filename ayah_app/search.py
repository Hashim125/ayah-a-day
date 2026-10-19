"""Ranked English/Arabic search and reviewed theme selection."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import config
from .data import QuranRepository, SURAH_AYAH_COUNTS, Verse

ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
WORD_RE = re.compile(r"[\w']+", re.UNICODE)
QURAN_MARKS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u06f0-\u06f9]")
THEME_KEYWORDS = {
    "Prayer & Worship": ("prayer", "worship", "prostrate", "remembrance"),
    "Faith & Belief": ("believe", "faith", "trust", "believer"),
    "Patience & Perseverance": ("patience", "steadfast", "persevere", "endure"),
    "Forgiveness & Mercy": ("forgive", "mercy", "pardon", "merciful"),
    "Guidance & Wisdom": ("guidance", "wisdom", "knowledge", "straight path"),
    "Paradise & Afterlife": ("paradise", "resurrection", "judgment", "garden"),
    "Charity & Giving": ("charity", "spend", "poor", "needy"),
    "Justice & Righteousness": ("justice", "righteous", "fair", "good deed"),
    "Fear & Hope": ("fear", "hope", "reverence", "despair"),
    "Family & Relationships": ("parent", "child", "spouse", "mother", "father"),
    "Struggle & Hardship": ("trial", "hardship", "difficulty", "adversity"),
    "Gratitude & Thankfulness": ("grateful", "thank", "blessing", "favor"),
}


def normalize_english(text: str) -> str:
    return " ".join(WORD_RE.findall(unicodedata.normalize("NFKC", text).casefold()))


def normalize_arabic(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = QURAN_MARKS_RE.sub("", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.translate(str.maketrans({"ٱ": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True, slots=True)
class SearchResult:
    verse: Verse
    score: int
    source: str = ""
    query: str = ""
    is_arabic: bool = False

    @property
    def snippet(self) -> str:
        # Built on demand: a search can match 1,500+ verses but a page shows ten.
        return make_snippet(self.source, self.query, self.is_arabic) if self.source else ""


class SearchService:
    def __init__(self, repository: QuranRepository):
        self.repository = repository
        # Normalized English is single-space-joined words, so padding it with spaces lets
        # " word " substring checks test whole-word membership without per-verse word sets.
        normalized_tafsir: dict[str, str] = {}
        self._index = {}
        for verse in repository.verses:
            tafsir = normalized_tafsir.get(verse.tafsir_plain)
            if tafsir is None:
                tafsir = normalized_tafsir[verse.tafsir_plain] = f" {normalize_english(verse.tafsir_plain)} "
            self._index[verse.verse_key] = (
                f" {normalize_english(verse.translation_text)} ", tafsir, normalize_arabic(verse.quran_text)
            )
        self._search_cache: dict[str, list[SearchResult]] = {}
        self._theme_cache: dict[str, list[SearchResult]] = {}
        path = Path(__file__).with_name("curation.json")
        self.curation = json.loads(path.read_text(encoding="utf-8"))
        self._validate_curation()

    def _validate_curation(self) -> None:
        if self.curation.get("status") not in {"draft", "approved"}:
            raise ValueError("Curation status must be 'draft' or 'approved'")
        daily = self.curation.get("daily")
        themes = self.curation.get("themes")
        if not isinstance(daily, list) or not isinstance(themes, dict):
            raise ValueError("Curation must contain daily and themes collections")
        curated_keys = [*daily, *(key for values in themes.values() for key in values)]
        unknown = sorted({key for key in curated_keys if self.repository.get(key) is None})
        if unknown:
            raise ValueError(f"Unknown curated verse keys: {', '.join(unknown)}")
        if set(themes) != set(THEME_KEYWORDS):
            raise ValueError("Curated theme names do not match configured themes")

    @property
    def themes(self) -> tuple[str, ...]:
        return tuple(THEME_KEYWORDS)

    @property
    def curation_approved(self) -> bool:
        return self.curation.get("status") == "approved"

    def reference_results(self, query: str) -> list[SearchResult] | None:
        match = re.fullmatch(r"(\d{1,3}):(\d{1,3})(?:-(\d{1,3}))?", query)
        if not match:
            return None
        surah, start = int(match[1]), int(match[2])
        end = int(match[3] or start)
        if not 1 <= surah <= 114 or start > end or start < 1 or end > SURAH_AYAH_COUNTS[surah - 1]:
            return []
        return [SearchResult(self.repository.get(f"{surah}:{ayah}"), 1000) for ayah in range(start, end + 1)]

    def search(self, query: str) -> list[SearchResult]:
        """Return ranked results. Callers must not mutate the returned list; it is cached."""
        query = query.strip()[:config.MAX_QUERY_LENGTH]
        if len(query) < config.MIN_QUERY_LENGTH:
            return []
        cached = self._search_cache.get(query)
        if cached is None:
            if len(self._search_cache) >= 256:
                self._search_cache.pop(next(iter(self._search_cache)))
            cached = self._search_cache[query] = self._search(query)
        return cached

    def _search(self, query: str) -> list[SearchResult]:
        references = self.reference_results(query)
        if references is not None:
            return references
        is_arabic = bool(ARABIC_RE.search(query))
        normalized = normalize_arabic(query) if is_arabic else normalize_english(query)
        tokens = set(normalized.split())
        padded_tokens = [f" {token} " for token in tokens]
        padded_query = f" {normalized} "
        results: list[SearchResult] = []
        for verse in self.repository.verses:
            translation, tafsir, arabic = self._index[verse.verse_key]
            score = 0
            source = ""
            if is_arabic:
                if normalized in arabic:
                    score, source = 700 + len(tokens), verse.quran_text
            else:
                if padded_query == translation:
                    score, source = 900, verse.translation_text
                elif normalized in translation:
                    score, source = 700 + len(tokens) * 10, verse.translation_text
                elif tokens and all(token in translation for token in padded_tokens):
                    score, source = 500 + len(tokens) * 10, verse.translation_text
                elif normalized in tafsir:
                    score, source = 200 + len(tokens), verse.tafsir_plain
                elif tokens and all(token in tafsir for token in padded_tokens):
                    score, source = 100 + len(tokens), verse.tafsir_plain
            if score:
                results.append(SearchResult(verse, score, source, normalized, is_arabic))
        return sorted(results, key=lambda item: (-item.score, item.verse.surah, item.verse.ayah))

    def theme_results(self, theme: str) -> list[SearchResult]:
        if theme not in THEME_KEYWORDS:
            return []
        if self.curation_approved:
            return [SearchResult(self.repository.get(key), 1000) for key in self.curation["themes"].get(theme, [])]
        if theme not in self._theme_cache:
            self._theme_cache[theme] = self._ranked_theme_results(theme)
        return self._theme_cache[theme]

    def _ranked_theme_results(self, theme: str) -> list[SearchResult]:
        combined: dict[str, SearchResult] = {}
        for keyword in THEME_KEYWORDS[theme]:
            for result in self.search(keyword)[:15]:
                current = combined.get(result.verse.verse_key)
                if current is None or result.score > current.score:
                    combined[result.verse.verse_key] = result
        return sorted(combined.values(), key=lambda item: (-item.score, item.verse.surah, item.verse.ayah))[:config.MAX_THEME_RESULTS]


def make_snippet(text: str, query: str, is_arabic: bool, length: int = 220) -> str:
    if len(text) <= length:
        return text
    haystack = normalize_arabic(text) if is_arabic else normalize_english(text)
    position = haystack.find(query)
    # Normalization can shift offsets, so use the position only as a rough centering hint.
    start = max(0, min(len(text) - length, position - length // 3 if position >= 0 else 0))
    prefix = "…" if start else ""
    suffix = "…" if start + length < len(text) else ""
    return f"{prefix}{text[start:start + length].strip()}{suffix}"
