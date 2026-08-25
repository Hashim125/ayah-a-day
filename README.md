# Ayah App

Ayah App is a quiet, reading-first Flask application for exploring the Quran with Mufti Taqi Usmani's English translation and Tafsir Ibn Kathir. It includes a London-time verse of the day, ranked English and Arabic search, reviewed-theme infrastructure, local bookmarks, sharing, and surrounding verse context.

## Run locally

Python 3.12 is the production target.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python simple_app.py
```

Open `http://127.0.0.1:5000`. The application fails at startup if the required data is absent or invalid.

## Test

```bash
pytest -q
```

The suite validates all 6,236 verses, exact Arabic source preservation, Tafsir references and sanitization, search behavior, API compatibility, security headers, and page response sizes.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `AYAH_DATA_DIR` | `./data` | Absolute or relative dataset directory |
| `APP_TIMEZONE` | `Europe/London` | Calendar used for the daily verse |
| `PUBLIC_BASE_URL` | Request origin | Canonical URL used in public links and metadata |
| `DEBUG` | `false` | Enable Flask development debugging |
| `HOST` | `127.0.0.1` | Local development bind address |
| `PORT` | `5000` locally | HTTP port |
| `WEB_CONCURRENCY` | `2` | Gunicorn workers |
| `GUNICORN_THREADS` | `4` | Threads per Gunicorn worker |

## Routes and API

- `/` — verse of the day
- `/random` — random verse
- `/search?q=mercy` — ranked English, Arabic, or reference search
- `/verse/2:255` — permanent verse page with Tafsir and context
- `/bookmarks` — browser-local saved verses
- `/curation-review` — no-index review page for draft daily and theme collections
- `/healthz` — readiness status

Existing JSON routes remain compatible: `/api/random`, `/api/verse-of-the-day`, `/api/search`, `/api/theme/<theme>`, and `/api/verse/<verse_key>`.

Search and theme APIs accept `limit` (1–50), `offset`, and `include_tafsir=0|1`. Pagination metadata is returned in `X-Total-Count`, `X-Limit`, `X-Offset`, and `Link` headers. Tafsir remains included by default for compatibility; new clients should request `include_tafsir=0` for compact results.

## Curation

[`ayah_app/curation.json`](ayah_app/curation.json) contains candidate daily and theme verse lists with `"status": "draft"`. While draft, the daily verse is selected deterministically from all verses and themes use ranked text search. Change the status only after the verse keys and translations receive human review.

## Render deployment

The included [`render.yaml`](render.yaml) installs the pinned dependencies, starts `gunicorn -c gunicorn.conf.py simple_app:app`, and checks `/healthz`. Set `PUBLIC_BASE_URL` to the final Render or custom-domain origin. No database or persistent disk is required.

## Data and typography

The repository expects:

- `data/qpc-hafs.json`
- `data/en-taqi-usmani-simple.json`
- `data/en-tafisr-ibn-kathir.json`

Treat Quran and translation content as immutable source material. Derived search normalization must never replace displayed text. Amiri is bundled under the SIL Open Font License in `static/fonts/OFL.txt`.
