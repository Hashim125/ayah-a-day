"""Ayah App application factory."""

from flask import Flask, request

import config
from .data import QuranRepository
from .search import SearchService


def create_app(*, repository: QuranRepository | None = None, testing: bool = False) -> Flask:
    app = Flask(__name__, static_folder=str(config.STATIC_FOLDER), template_folder="templates")
    app.config.update(TESTING=testing, DEBUG=config.DEBUG_MODE if not testing else False)
    app.extensions["quran_repository"] = repository or QuranRepository.load()
    # Build the search index at startup (shared by gunicorn's preloaded workers) so the
    # first visitor to search doesn't wait for it.
    app.extensions["search_service"] = SearchService(app.extensions["quran_repository"])

    from .routes import pages
    app.register_blueprint(pages)

    @app.context_processor
    def asset_context():
        return {"asset_version": config.STATIC_ASSET_VERSION}

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
        if request.endpoint == "static":
            response.cache_control.no_cache = False
            response.cache_control.public = True
            response.cache_control.max_age = 31_536_000
            response.cache_control.immutable = True
        return response

    return app
