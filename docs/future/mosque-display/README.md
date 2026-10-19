# Mosque display (parked)

A full-screen page for a prayer-hall TV that shows the day's verse with a QR code to its Tafsir. It was built and tested in October 2026, then taken out of the app until the project is ready for it. Everything needed to restore it is in this folder.

## What it does

- `/display` shows today's verse (the same one as the home page) full screen, with no navigation.
- The header shows the mosque name, the Gregorian date and the Hijri (Umm al-Qura) date.
- The footer shows an optional notice line and a QR code that opens `/verse/<key>` with the Tafsir and surrounding verses.
- `/display?key=2:282` previews any verse. Invalid keys return 400 and unknown verses return 404.
- `/display/qr.svg?key=…` serves the QR code as an SVG image, cached for an hour.
- The page reloads about 30 seconds after midnight in `APP_TIMEZONE`. It checks `/healthz` first and retries every minute if the server doesn't answer, so the screen never lands on a browser error page.
- It asks the browser to keep the screen awake (Wake Lock API) and asks again when the tab becomes visible.
- Long verses shrink until they fit the screen. 2:282, the longest, was tested at 1920×1080.

It shows the verse only, not prayer times. That is deliberate (see below).

## Why it was scoped this way

Mosque TV screens are already a crowded market, and most of them are built around prayer and iqamah times:

- **Mawaqit**: free for mosques and run as a non-profit. Has its own TV box that works offline, plus an Android TV app.
- **Masjidbox Screens**: any HDMI TV, managed from a phone. Prayer times, iqamah countdowns, announcements and Quranic verses.
- **Masjidi**: a free Google TV app with iqamah countdowns, rotating hadith and adhkar.
- **Masjidal (Al-Iqamah)** and **Ad-Din**: paid iqamah-time displays.
- **WordPress plugins**: MasjidOS, and Daily Prayer Time, which has a random-verse shortcode.

Ayah shouldn't compete on prayer times. What it can offer is a reviewed daily verse with Tafsir, a QR code to read more, and a better-looking screen. The plan was for it to run beside a mosque's existing prayer-times screen, or between prayers.

## Files in this folder

| File | Goes to | Notes |
| --- | --- | --- |
| `display.html` | `ayah_app/templates/display.html` | A standalone template that doesn't extend `base.html`. It reuses `verse_key_block` and `verse_text` from `_verse_card.html` and `arch` from `_icons.html`. |
| `display.js` | `static/display.js` | Hijri date, fit-to-screen, wake lock and midnight reload. Avoids `?.` and numeric separators for older TV browsers. |
| `display.css` | the end of `static/app.css`, above `/* Responsive */` | Uses the app's colour tokens. The page's base size is `min(1.25vw, 2.22vh)`, about 24px on a 1080p screen. |
| `routes_snippet.py` | `ayah_app/routes.py`, above the curation-review route | Also add `import io`, `import segno`, and `Response` to the flask import. |
| `config_snippet.py` | `config.py`, after `PUBLIC_BASE_URL` | `MOSQUE_NAME`, `MOSQUE_NOTICE`, `HIJRI_OFFSET_DAYS`. |
| `readme_rows.md` | the configuration table in the main `README.md` | |
| `test_snippet.py` | the end of `tests/test_app.py` | Also add `/display` and `/display?key=2:282` back to `test_pages_have_no_inline_styles_or_scripts`. |

Also add `segno==1.6.6` to `requirements.txt` for the QR code.

## Restore checklist

1. Copy the files back as listed above, and re-add `segno`.
2. Bump `STATIC_ASSET_VERSION` in `config.py`.
3. Run `pytest -q` and `node --check static/display.js`.
4. Open `/display` and `/display?key=2:282` at 1920×1080 and check that the verse fits and the QR code scans.
5. **Set `PUBLIC_BASE_URL` in Render before mosques use it.** It isn't in `render.yaml`. Without it, the QR code encodes the request's own host and scheme, which behind Render's proxy is likely plain `http://`.
6. Set `MOSQUE_NAME` (and optionally `MOSQUE_NOTICE`, `HIJRI_OFFSET_DAYS`) for each mosque deployment.

## Known limits and open questions

- **Not tested on real TV hardware.** The script needs a browser from roughly 2017 or later (Chrome 60+). Some cheap smart-TV browsers are older.
- **Hijri date:** this uses the Umm al-Qura calendar. Many UK mosques follow local moon sighting, which is why `HIJRI_OFFSET_DAYS` (−2 to 2) exists. It's set per deployment, not per mosque.
- **One mosque per deployment.** The name and notice come from environment variables. Serving several mosques would need per-mosque settings, for example `/display/<slug>` backed by a small config file.
- **The daily verse isn't reviewed yet.** `curation.json` is still a draft, so the screen can show any of the 6,236 verses. Approving the daily list first is a good idea before putting it in a prayer hall.
- **Before investing further**, check whether Mawaqit or Masjidbox accept outside content such as an embed or feed. If they do, a "verse of the day" feed for those systems might reach more mosques than a separate screen.

## Ideas for later

- An imam approval screen for the daily verse list, building on `/curation-review`.
- Pinning a verse for Jumu'ah, Ramadan nights or events.
- A printable A4 noticeboard poster of the week's verse with the QR code.
- A "Copy for WhatsApp" button for mosque broadcast groups.
