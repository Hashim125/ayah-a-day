"""HTML pages and backward-compatible JSON APIs."""

from __future__ import annotations

import datetime as dt
import random
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, current_app, jsonify, render_template, request, url_for

import config
from .data import QuranRepository, VERSE_KEY_RE, Verse
from .search import SearchResult, SearchService

pages = Blueprint("pages", __name__)
_system_random = random.SystemRandom()


def repository() -> QuranRepository:
    return current_app.extensions["quran_repository"]


def search_service() -> SearchService:
    service = current_app.extensions.get("search_service")
    if service is None:
        service = SearchService(repository())
        current_app.extensions["search_service"] = service
    return service


def public_url(endpoint: str, **values) -> str:
    relative = url_for(endpoint, **values)
    return f"{config.PUBLIC_BASE_URL}{relative}" if config.PUBLIC_BASE_URL else url_for(endpoint, _external=True, **values)


def verse_payload(verse: Verse, *, include_tafsir: bool = True) -> dict:
    payload = {
        "clean_ayah_text": verse.quran_text,
        "translation_text": verse.translation_text,
        "surah_number": verse.surah,
        "ayah_number": verse.ayah,
        "verse_key": verse.verse_key,
        "surah_name": verse.surah_name,
    }
    if include_tafsir:
        payload["tafsir_html_content"] = verse.tafsir_html
    return payload


def page_args(default_limit: int = config.MAX_SEARCH_RESULTS) -> tuple[int, int, bool]:
    try:
        offset = max(0, int(request.args.get("offset", "0")))
        limit = int(request.args.get("limit", str(default_limit)))
    except ValueError:
        abort(400, "Pagination values must be integers")
    limit = max(1, min(config.MAX_API_PAGE_SIZE, limit))
    include_tafsir = request.args.get("include_tafsir", "1") not in {"0", "false", "no"}
    return offset, limit, include_tafsir


def paginated_json(items: list[SearchResult], *, enveloped: bool = False, theme: str = "", default_limit: int = config.MAX_SEARCH_RESULTS):
    offset, limit, include_tafsir = page_args(default_limit)
    page = items[offset:offset + limit]
    payloads = [verse_payload(item.verse, include_tafsir=include_tafsir) for item in page]
    body = {"theme": theme, "count": len(items), "results": payloads} if enveloped else payloads
    response = jsonify(body)
    response.headers["X-Total-Count"] = str(len(items))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    links = []
    base_args = {key: value for key, value in request.args.items() if key not in {"offset", "limit"}}
    if offset:
        previous = max(0, offset - limit)
        links.append(f'<{request.path}?{urlencode({**base_args, "offset": previous, "limit": limit})}>; rel="prev"')
    if offset + limit < len(items):
        links.append(f'<{request.path}?{urlencode({**base_args, "offset": offset + limit, "limit": limit})}>; rel="next"')
    if links:
        response.headers["Link"] = ", ".join(links)
    return response


def daily_verse() -> tuple[Verse, dt.date, bool]:
    service = search_service()
    today = dt.datetime.now(ZoneInfo(config.APP_TIMEZONE)).date()
    if service.curation_approved and service.curation.get("daily"):
        keys = service.curation["daily"]
        key = keys[today.toordinal() % len(keys)]
        return repository().get(key), today, True
    rng = random.Random(today.isoformat())
    return repository().get(rng.choice(repository().keys)), today, False


@pages.app_context_processor
def template_context():
    return {"app_name": config.APP_NAME, "verse_count": len(repository())}


@pages.get("/")
def home():
    verse, today, curated = daily_verse()
    response = current_app.make_response(render_template(
        "verse.html", verse=verse, page_kind="daily", page_title="Verse of the Day",
        display_date=today.strftime("%A, %d %B %Y"), curated=curated,
        previous_key=repository().previous_key(verse), next_key=repository().next_key(verse),
        context_before=[], context_after=[], canonical_url=public_url("pages.home"),
    ))
    response.cache_control.public = True
    response.cache_control.max_age = 300
    return response


@pages.get("/random")
def random_page():
    verse = repository().get(_system_random.choice(repository().keys))
    return render_template(
        "verse.html", verse=verse, page_kind="random", page_title="Random Ayah",
        previous_key=repository().previous_key(verse), next_key=repository().next_key(verse),
        context_before=[], context_after=[], canonical_url=public_url("pages.random_page"),
    )


@pages.get("/verse/<verse_key>")
def verse_page(verse_key: str):
    if not VERSE_KEY_RE.fullmatch(verse_key):
        abort(400, "Use a verse reference such as 2:255")
    verse = repository().get(verse_key)
    if verse is None:
        abort(404)
    before, after = repository().neighbors(verse)
    return render_template(
        "verse.html", verse=verse, page_kind="verse",
        page_title=f"{verse.surah_name} {verse.verse_key}",
        previous_key=repository().previous_key(verse), next_key=repository().next_key(verse),
        context_before=before, context_after=after,
        canonical_url=public_url("pages.verse_page", verse_key=verse.verse_key),
        description=verse.translation_text[:200],
    )


@pages.get("/search")
def search_page():
    query = request.args.get("q", "").strip()[:config.MAX_QUERY_LENGTH]
    theme = request.args.get("theme", "").strip()[:100]
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    results = search_service().theme_results(theme) if theme else search_service().search(query) if query else []
    per_page = 10
    total_pages = max(1, (len(results) + per_page - 1) // per_page)
    page = min(page, total_pages)
    shown = results[(page - 1) * per_page:page * per_page]
    return render_template(
        "search.html", query=query, selected_theme=theme, themes=search_service().themes,
        results=shown, total=len(results), page=page, total_pages=total_pages,
        curation_approved=search_service().curation_approved, page_title="Search",
    )


@pages.get("/bookmarks")
def bookmarks_page():
    return render_template("bookmarks.html", page_title="Bookmarks")


@pages.get("/curation-review")
def curation_review():
    service = search_service()
    daily = [repository().get(key) for key in service.curation["daily"]]
    themes = {
        name: [repository().get(key) for key in keys]
        for name, keys in service.curation["themes"].items()
    }
    return render_template(
        "curation_review.html", page_title="Curation review", daily=daily,
        curated_themes=themes, status=service.curation["status"], noindex=True,
    )


@pages.get("/api/random")
def api_random():
    verse = repository().get(_system_random.choice(repository().keys))
    include = request.args.get("include_tafsir", "1") not in {"0", "false", "no"}
    return jsonify(verse_payload(verse, include_tafsir=include))


@pages.get("/api/verse-of-the-day")
def api_daily():
    verse, _, _ = daily_verse()
    include = request.args.get("include_tafsir", "1") not in {"0", "false", "no"}
    response = jsonify(verse_payload(verse, include_tafsir=include))
    response.cache_control.public = True
    response.cache_control.max_age = 300
    return response


@pages.get("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    return paginated_json(search_service().search(query))


@pages.get("/api/theme/<path:theme_name>")
def api_theme(theme_name: str):
    # Preserve the historical default of five theme results.
    return paginated_json(search_service().theme_results(theme_name), enveloped=True, theme=theme_name, default_limit=5)


@pages.get("/api/verse/<verse_key>")
def api_verse(verse_key: str):
    verse = repository().get(verse_key)
    if verse is None:
        return jsonify({"error": "Verse not found"}), 404
    include = request.args.get("include_tafsir", "1") not in {"0", "false", "no"}
    return jsonify(verse_payload(verse, include_tafsir=include))


@pages.get("/healthz")
def health():
    return jsonify({"status": "ready", "verses": len(repository())})


@pages.app_errorhandler(400)
def bad_request(error):
    return render_template("error.html", page_title="Invalid request", code=400,
                           message=getattr(error, "description", "The request was invalid.")), 400


@pages.app_errorhandler(404)
def not_found(_error):
    return render_template("error.html", page_title="Page not found", code=404,
                           message="The page or verse you requested could not be found."), 404


@pages.app_errorhandler(500)
def server_error(_error):
    return render_template("error.html", page_title="Something went wrong", code=500,
                           message="The request could not be completed."), 500
