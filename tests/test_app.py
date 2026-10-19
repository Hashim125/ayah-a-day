import re


def test_core_pages_render(client):
    for path in ("/", "/random", "/search", "/search?q=mercy", "/verse/2:255", "/bookmarks", "/curation-review"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert b"Content-Security-Policy" not in response.data
        assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_search_input_is_escaped(client):
    payload = '"><script>alert(1)</script>'
    response = client.get("/search", query_string={"q": payload})
    assert response.status_code == 200
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data


def test_search_page_is_compact(client):
    response = client.get("/search?q=mercy")
    assert response.status_code == 200
    assert len(response.data) < 150_000


def test_api_default_shape_is_compatible(client):
    verse = client.get("/api/verse/2:255").get_json()
    assert {"clean_ayah_text", "translation_text", "tafsir_html_content", "surah_number", "ayah_number", "verse_key"} <= set(verse)
    results = client.get("/api/search?q=mercy").get_json()
    assert isinstance(results, list)
    assert results and "tafsir_html_content" in results[0]


def test_api_supports_compact_pagination(client):
    response = client.get("/api/search?q=mercy&limit=3&offset=1&include_tafsir=0")
    body = response.get_json()
    assert len(body) == 3
    assert "tafsir_html_content" not in body[0]
    assert response.headers["X-Limit"] == "3"
    assert response.headers["X-Offset"] == "1"
    assert int(response.headers["X-Total-Count"]) >= 4
    assert 'rel="next"' in response.headers["Link"]


def test_theme_api_preserves_five_result_default(client):
    response = client.get("/api/theme/Faith%20%26%20Belief")
    payload = response.get_json()
    assert payload["theme"] == "Faith & Belief"
    assert len(payload["results"]) <= 5
    assert payload["count"] >= len(payload["results"])


def test_daily_is_stable_and_health_is_ready(client):
    first = client.get("/api/verse-of-the-day?include_tafsir=0").get_json()
    second = client.get("/api/verse-of-the-day?include_tafsir=0").get_json()
    assert first["verse_key"] == second["verse_key"]
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ready", "verses": 6236}


def test_reader_uses_compact_progressive_disclosure(client):
    daily = client.get("/").data
    assert b'class="reader-kicker"' in daily
    assert b'data-tafsir-toggle' in daily
    assert b'class="share-menu"' in daily
    assert b'data-font-size' not in daily
    verse = client.get("/verse/2:255").data
    assert b'data-context-toggle' in verse
    assert b'id="nearby-verses" hidden' in verse


def test_invalid_routes_have_safe_errors(client):
    assert client.get("/verse/not-a-reference").status_code == 400
    response = client.get("/verse/999:999")
    assert response.status_code == 404
    assert not re.search(rb"Traceback|DataIntegrityError", response.data)


def test_pages_have_no_inline_styles_or_scripts(client):
    # The CSP allows only 'self' for styles and scripts, so inline ones would be silently dropped.
    for path in ("/", "/verse/2:282", "/search?q=mercy", "/bookmarks", "/random", "/curation-review"):
        html = client.get(path).data
        assert b'style="' not in html, path
        assert not re.search(rb"<script(?![^>]*\bsrc=)", html), path


def test_search_results_come_before_themes(client):
    # Results must be visible without scrolling past the twelve theme tiles.
    for path in ("/search?q=patience", "/search?theme=Faith+%26+Belief"):
        html = client.get(path).data
        assert html.index(b'id="results-title"') < html.index(b'id="themes-title"'), path
