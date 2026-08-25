# Ayah App repository guidance

The active application is a Flask package in `ayah_app/`; `simple_app.py` is only the compatible WSGI and local-development entrypoint.

## Architecture

- `ayah_app/data.py` validates, resolves, sanitizes, and exposes immutable verse data.
- `ayah_app/search.py` owns normalization, ranking, themes, and curation state.
- `ayah_app/routes.py` owns HTML and backward-compatible JSON routes.
- `ayah_app/templates/` and `static/app.*` own presentation and browser behavior.
- `tests/` includes full-dataset integrity, security, route, and search checks.

## Non-negotiable invariants

- Never modify or normalize Quran text in place. Display the exact loaded Arabic string.
- Keep verse-key alignment across Arabic, translation, and Tafsir datasets.
- Do not render user-controlled strings through `|safe`, HTML concatenation, or `innerHTML`.
- Tafsir is the only allowed rich-text field and must pass through the configured `nh3` allowlist.
- Preserve existing route names and default API body shapes unless a breaking version is explicitly requested.
- Do not mark `curation.json` approved without human review of its verse keys and translations.

Run `pytest -q` and `node --check static/app.js` after application changes.
