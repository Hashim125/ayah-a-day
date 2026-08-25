import json

import pytest

import config
from ayah_app.data import DataIntegrityError, QuranRepository, sanitize_tafsir
from ayah_app.search import SearchService, normalize_arabic


def sources(tafsir=None):
    quran = {"1:1": {"surah": 1, "ayah": 1, "text": "بِسْمِ اللَّهِ"}}
    translation = {"1:1": {"t": "In the name of Allah."}}
    return quran, translation, tafsir or {"1:1": {"text": "<p>Commentary</p>"}}


def test_full_repository_has_every_verse(repository):
    assert len(repository) == 6236
    assert repository.keys[0] == "1:1"
    assert repository.keys[-1] == "114:6"


def test_arabic_source_is_preserved_exactly(repository):
    with config.get_data_file_path("quran").open(encoding="utf-8") as handle:
        raw = json.load(handle)
    assert all(repository.get(key).quran_text == entry["text"] for key, entry in raw.items())


def test_sanitizer_keeps_reading_markup_and_removes_active_content():
    result = sanitize_tafsir('<p lang="en" onclick="bad()">Safe</p><script>alert(1)</script><img src=x onerror=bad()>')
    assert "<p lang=\"en\">Safe</p>" in result
    assert "alert" not in result
    assert "onclick" not in result
    assert "img" not in result


def test_loader_rejects_mismatched_keys():
    quran, translation, tafsir = sources()
    translation["1:2"] = {"t": "Extra"}
    with pytest.raises(DataIntegrityError, match="key sets differ"):
        QuranRepository.from_sources(quran, translation, tafsir)


def test_loader_rejects_tafsir_cycle():
    quran = {
        "1:1": {"surah": 1, "ayah": 1, "text": "a"},
        "1:2": {"surah": 1, "ayah": 2, "text": "b"},
    }
    translation = {"1:1": "one", "1:2": "two"}
    with pytest.raises(DataIntegrityError, match="Cyclic Tafsir"):
        QuranRepository.from_sources(quran, translation, {"1:1": "1:2", "1:2": "1:1"})


def test_arabic_search_ignores_diacritics(repository):
    service = SearchService(repository)
    assert normalize_arabic("ٱلرَّحْمَٰنِ") == normalize_arabic("الرحمن")
    assert any(result.verse.verse_key == "1:1" for result in service.search("الرحمن"))


def test_reference_ranges_are_validated(repository):
    service = SearchService(repository)
    assert [item.verse.verse_key for item in service.search("2:255-257")] == ["2:255", "2:256", "2:257"]
    assert service.search("2:286-287") == []
    assert service.search("2:10-3") == []


def test_translation_matches_rank_above_tafsir_matches(repository):
    results = SearchService(repository).search("Most Merciful")
    assert results
    translation_matches = [r for r in results if "most merciful" in r.verse.translation_text.casefold()]
    assert translation_matches
    assert translation_matches[0].score >= results[-1].score
