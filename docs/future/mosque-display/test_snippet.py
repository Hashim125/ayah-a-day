# Removed from tests/test_app.py. Also add "/display", "/display?key=2:282" back to
# test_pages_have_no_inline_styles_or_scripts.
import re


def test_mosque_display_shows_requested_verse(client, repository):
    response = client.get("/display?key=2:282")
    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    html = response.get_data(as_text=True)
    assert repository.get("2:282").quran_text in html
    assert 'class="site-header"' not in html
    assert "/display/qr.svg?key=2:282" in html
    assert client.get("/display").status_code == 200


def test_mosque_display_rejects_bad_keys(client):
    assert client.get("/display?key=not-a-key").status_code == 400
    assert client.get("/display?key=999:999").status_code == 404


def test_display_qr_is_svg(client):
    response = client.get("/display/qr.svg?key=94:5")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert response.data.lstrip().startswith(b"<svg")
