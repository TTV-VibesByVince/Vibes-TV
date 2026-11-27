"""Vibesmas: alerts as a holiday train, and the hype train video."""
import struct
import time

import vibesmas as V

SETTINGS = {"vibesmas": "auto", "vibesmas_from": "11-25", "vibesmas_to": "12-31"}


def day(md):
    return time.strptime("2026-" + md, "%Y-%m-%d")


def who(name, avatar=""):
    return {"login": name.lower(), "display_name": name, "avatar": avatar}


def mp4(seconds, version=0):
    """The smallest file mp4_seconds can read: an mvhd box with a timescale and duration."""
    if version == 0:
        body = bytes([0, 0, 0, 0]) + struct.pack(">IIII", 0, 0, 600, int(seconds * 600))
    else:
        body = bytes([1, 0, 0, 0]) + struct.pack(">QQIQ", 0, 0, 1000, int(seconds * 1000))
    return b"\x00\x00\x00\x20ftypisom" + struct.pack(">I", len(body) + 8) + b"mvhd" + body + bytes(80)


def test_dates():
    assert V.active(SETTINGS, day("11-25")) and V.active(SETTINGS, day("12-31"))
    assert not V.active(SETTINGS, day("11-24")) and not V.active(SETTINGS, day("01-01"))
    wrap = {**SETTINGS, "vibesmas_from": "12-15", "vibesmas_to": "01-05"}
    assert V.active(wrap, day("01-03")) and V.active(wrap, day("12-20")) and not V.active(wrap, day("06-01"))
    assert V.active({**SETTINGS, "vibesmas": "on"}, day("07-04"))
    assert not V.active({**SETTINGS, "vibesmas": "off"}, day("12-25"))
    assert not V.active({**SETTINGS, "vibesmas_from": "13-01"}, day("12-25"))


def test_trains():
    t = V.train_for("follow", {"user": who("Pal")})
    assert [c["car"] for c in t["cars"]] == ["loco", "tender", "coach", "caboose"]
    assert t["cars"][0]["label"] == "NEW FOLLOW" and t["cars"][2]["who"]["name"] == "Pal"
    assert t["cars"][-1]["text"] == "HAPPY VIBESMAS" and t["seconds"] == V.SHORT_SECONDS

    t = V.train_for("sub", {"user": who("Big"), "tier_level": 3, "months": 12, "text": {"message": "Merry!"}})
    coach = t["cars"][2]
    assert coach["first"] and coach["sub"] == "12 MONTHS · TIER 3" and t["cars"][-1] == {"car": "banner", "text": "Merry!"}

    # 25 gifts, 12 names known: the gifter in first class, 10 cars, and the rest on the caboose
    riders = [who(f"Kid{i}") for i in range(12)]
    t = V.train_for("gift", {"user": who("Santa"), "count": 25, "recipients": riders})
    cars = t["cars"]
    assert cars[0]["label"] == "25 GIFT SUBS" and cars[2]["first"] and cars[2]["sub"] == "GIFTED 25 SUBS"
    assert sum(1 for c in cars if c["car"] == "coach") == 11 and cars[3]["sub"] == "GIFT FROM SANTA"
    assert cars[-1] == {"car": "caboose", "text": "+15 PASSENGERS", "sub": "ALSO ABOARD"}
    assert t["seconds"] > V.SHORT_SECONDS                     # a long train crawls

    t = V.train_for("gift", {"user": who("Santa"), "count": 1, "recipients": [who("Kid")]})
    assert t["cars"][0]["label"] == "1 GIFT SUB" and t["cars"][-1]["text"] == "HAPPY VIBESMAS"

    t = V.train_for("bits", {"user": who("Cheer"), "amount": 1500, "text": {"message": "choo choo"}})
    assert [c["car"] for c in t["cars"]].count("coal") == 2 and t["cars"][0]["label"] == "1,500 BITS"

    t = V.train_for("raid", {"user": who("Raider"), "viewers": 120})
    assert [c["car"] for c in t["cars"]].count("crowd") == 3 and t["cars"][-1]["text"] == "120 PASSENGERS"
    assert t["length"] == sum(V.WIDTHS[c["car"]] for c in t["cars"])


def test_video_length(tmp_path):
    p = tmp_path / "a.mp4"
    p.write_bytes(mp4(7.93))
    assert V.mp4_seconds(p) == 7.93
    p.write_bytes(mp4(12.5, version=1))
    assert V.mp4_seconds(p) == 12.5
    p.write_bytes(b"not a video")
    assert V.mp4_seconds(p) is None


async def test_alerts_ride_the_train(client, tv, overlay, srv):
    srv.S.data.update(vibesmas="on", vibesmas_overlay=True)
    await client.get("/follow/Pal")
    ev = await tv.next("follow")
    assert ev["train"]["cars"][0]["label"] == "NEW FOLLOW" and ev["card_seconds"] == V.SHORT_SECONDS
    ov = await overlay.next("follow")
    assert ov["train"] and "size" not in ov


async def test_overlay_can_keep_cards(client, tv, overlay, srv):
    srv.S.data.update(vibesmas="on", vibesmas_overlay=False)
    await client.get("/follow/Pal")
    assert (await tv.next("follow"))["train"]
    assert "train" not in await overlay.next("follow")


async def test_off_means_cards(client, tv, srv):
    srv.S.data.update(vibesmas="off")
    await client.get("/follow/Pal")
    assert "train" not in await tv.next("follow")


async def test_hype_video(client, tv, srv):
    (srv.MEDIA / "hype.mp4").write_bytes(mp4(8))
    r = await client.post("/api/settings", json={"vibesmas": "on", "vibesmas_hype_video": "hype.mp4", "vibesmas_hype_volume": 0.4})
    assert (await r.json())["ok"]
    await client.get("/hypetrain/start?level=1&percent=10")
    ev = await tv.next("hype_video")
    assert ev["video"] == {"src": "/media/hype.mp4", "seconds": 8.0, "volume": 0.4} and ev["title"] == "HYPE TRAIN"
    await client.get("/hypetrain/progress?level=2&percent=10")      # a level-up isn't a start: no second video
    assert await tv.next("hype_video", timeout=1) is None


async def test_no_video_no_intro(client, tv, srv):
    srv.S.data.update(vibesmas="on")
    await client.get("/hypetrain/start?level=1&percent=10")
    assert await tv.next("hype_video", timeout=1) is None


async def test_settings_checks(client, tv, srv):
    r = await (await client.post("/api/settings", json={"vibesmas_from": "13-40"})).json()
    assert not r["ok"]
    r = await (await client.post("/api/settings", json={"vibesmas_hype_video": "missing.mp4"})).json()
    assert not r["ok"]
    r = await (await client.post("/api/settings", json={"vibesmas_direction": "up"})).json()
    assert not r["ok"]
    assert tv.hello["vibesmas"] == {"on": False, "tv": True, "overlay": True, "dir": "ltr", "sound": True}
