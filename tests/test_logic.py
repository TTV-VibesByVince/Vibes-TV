"""Pure logic: text templates, colours, themes, settings validation."""
import io
import time

from PIL import Image


def test_text_placeholders_and_optional_parts(srv):
    t = srv.text_for
    assert t("raid.sub", game="Minecraft") == "is raiding from Minecraft with"
    assert t("raid.sub", game="") == "is raiding with"           # [bracket] part dropped
    assert t("shoutout.sub") == ""
    assert t("bits.title", amount="2,500") == "2,500 BITS!"
    assert t("resub.sub", tier="Prime") == "Thanks for resubscribing · Prime"


def test_text_overrides_and_reset(srv):
    assert srv.S.update({"texts": {"follow.title": "Welcome to the {name} crew!"}}) == []
    assert srv.text_for("follow.title", name="Pal") == "Welcome to the Pal crew!"
    srv.S.update({"texts": {"follow.title": ""}})                # blank = default again
    assert srv.text_for("follow.title") == "THANKS FOR THE FOLLOW!"
    srv.S.update({"texts": {"not.a.key": "x"}})
    assert "not.a.key" not in srv.S["texts"]


def test_event_colours(srv):
    assert srv.event_color("raid", "00ff00") == "00ff00"         # avatar colour by default
    assert srv.event_color("raid", None) == "9146ff"             # no avatar: theme colour
    srv.S.update({"colors": {"raid": "#FF0000", "follow": "theme"}})
    assert srv.event_color("raid", "00ff00") == "ff0000"
    assert srv.event_color("follow", "00ff00") == "9146ff"
    assert srv.S.update({"colors": {"bits": "rainbow"}}) != []


def test_theme_schedule_wraps_new_year(srv):
    srv.S.update({"theme": "valentine", "theme_schedule": [
        {"theme": "halloween", "from": "10-01", "to": "10-31"},
        {"theme": "holidays", "from": "12-15", "to": "01-05"}]})
    day = lambda d: srv.active_theme_id(time.strptime(d, "%Y-%m-%d"))
    assert day("2026-10-16") == "halloween"
    assert day("2026-12-20") == "holidays"
    assert day("2027-01-03") == "holidays"
    assert day("2027-03-01") == "valentine"                      # outside: the picked theme


def test_settings_validation(srv):
    assert srv.S.update({"card_seconds": 999}) != []
    assert srv.S.update({"govee_color_url": "ftp://x"}) != []
    assert srv.S.update({"logo": "../app/server.py"}) != []
    assert srv.S.update({"tv_mode": "turbo"}) != []
    assert srv.S.update({"theme": "nope"}) != []
    assert srv.S.update({"theme_schedule": [{"theme": "halloween", "from": "1-1", "to": "x"}]}) != []


def test_secret_handling(srv):
    srv.S.update({"twitch_client_secret": "abc"})
    assert "abc" not in str(srv.S.public()) and srv.S.public()["twitch_client_secret_set"]
    srv.S.update({"twitch_client_secret": ""})                   # blank keeps it
    assert srv.S["twitch_client_secret"] == "abc"
    srv.S.update({"twitch_client_secret": "-"})                  # "-" clears it
    assert srv.S["twitch_client_secret"] == ""


def test_avatar_colour_prefers_vivid(srv):
    img = Image.new("RGB", (100, 100), (20, 20, 20))
    for x in range(30, 70):
        for y in range(30, 70):
            img.putpixel((x, y), (255, 120, 0))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    r, g, b = (int(srv.dominant_hex(buf.getvalue())[i:i + 2], 16) for i in (0, 2, 4))
    assert r > 200 and b < 60                                    # orange, not the dark background
