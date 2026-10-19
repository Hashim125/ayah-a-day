"""Routes removed from ayah_app/routes.py. Paste back above the curation-review route.

Also needs: `import io`, `import segno`, and `Response` from flask.
"""

def requested_or_daily_verse() -> Verse:
    """Return the verse named by ?key= (used to preview a screen), or today's verse."""
    key = request.args.get("key", "").strip()
    if not key:
        return daily_verse()[0]
    if not VERSE_KEY_RE.fullmatch(key):
        abort(400, "Use a verse reference such as 2:255")
    verse = repository().get(key)
    if verse is None:
        abort(404)
    return verse


@pages.get("/display")
def display_page():
    verse = requested_or_daily_verse()
    now = dt.datetime.now(ZoneInfo(config.APP_TIMEZONE))
    # Reload just after local midnight so a mosque screen moves to the next day's verse.
    next_day = dt.datetime.combine(now.date() + dt.timedelta(days=1), dt.time(0, 0, 30), tzinfo=now.tzinfo)
    response = current_app.make_response(render_template(
        "display.html", verse=verse, page_title="Mosque display",
        display_date=f"{now:%A} {now.day} {now:%B %Y}",
        reload_seconds=int((next_day - now).total_seconds()),
        mosque_name=config.MOSQUE_NAME, mosque_notice=config.MOSQUE_NOTICE,
        timezone=config.APP_TIMEZONE, hijri_offset=config.HIJRI_OFFSET_DAYS,
    ))
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.cache_control.public = True
    response.cache_control.max_age = 60
    return response


@pages.get("/display/qr.svg")
def display_qr():
    verse = requested_or_daily_verse()
    buffer = io.BytesIO()
    segno.make_qr(public_url("pages.verse_page", verse_key=verse.verse_key), error="m").save(
        buffer, kind="svg", scale=1, border=2, dark="#2a1519", light="#ffffff", xmldecl=False,
    )
    response = Response(buffer.getvalue(), mimetype="image/svg+xml")
    response.cache_control.public = True
    response.cache_control.max_age = 3600
    return response
