"""1.5: the TV and the stream overlay are separate screens with their own
queues, routing per alert type, and their own settings."""
import asyncio
import json
import time

from aiohttp import web


async def test_hello_tells_each_screen_what_it_needs(client, tv, overlay):
    assert tv.hello["screen"] == "tv" and "logo" in tv.hello
    cfg = overlay.hello["overlay"]
    assert set(cfg) == {"position", "scale", "opacity", "seconds"}
    assert (cfg["position"], cfg["scale"], cfg["opacity"]) == ("bottom-left", 1.0, 0.85)


async def test_alerts_go_to_both_screens_by_default(client, tv, overlay):
    r = await client.get("/follow/Pal")
    assert (await r.json())["screens"] == ["tv", "overlay"]
    assert (await tv.next("follow"))["user"]["display_name"] == "Pal"
    assert (await overlay.next("follow"))["user"]["display_name"] == "Pal"


async def test_giant_emotes_are_tv_only_by_default(client, tv, overlay):
    await client.get("/gigantify/Fan?emote=25")
    assert await tv.next("gigantify")
    assert await overlay.next("gigantify", timeout=1) is None


async def test_routing_setting_and_url_override(client, srv, tv, overlay):
    srv.S.update({"routes": {"follow": "overlay"}})
    await client.get("/follow/OnlyOverlay")
    assert await overlay.next("follow")
    assert await tv.next("follow", timeout=1) is None
    await client.get("/follow/ForcedTV?screen=tv")              # ?screen= wins over the setting
    assert (await tv.next("follow"))["user"]["display_name"] == "ForcedTV"
    assert await overlay.next("follow", timeout=1) is None
    assert (await client.get("/follow/X?screen=fridge")).status == 400


async def test_resubs_follow_the_sub_route(client, srv, tv, overlay):
    srv.S.update({"routes": {"sub": "tv"}})
    await client.get("/resub/Loyal?months=3")
    assert await tv.next("resub")
    assert await overlay.next("resub", timeout=1) is None


async def test_overlay_uses_its_own_duration(client, srv, tv, overlay):
    srv.S.data["sub_seconds"] = 5
    srv.S.data["overlay_seconds"] = 0.3
    await client.get("/sub/Quick")
    assert (await tv.next("sub"))["card_seconds"] == 5
    assert (await overlay.next("sub"))["card_seconds"] == 0.3


async def test_overlay_does_not_wait_for_a_tv_clip(client, srv, tv, overlay, monkeypatch):
    """A raid with a 4-second clip holds the TV; the overlay plays its card,
    finishes, and goes on to the next alert while the TV clip is still going."""
    srv.S.update({"twitch_client_id": "id", "twitch_client_secret": "secret"})
    srv.S.data["overlay_seconds"] = 0.3

    async def user(login):
        return {"id": "42", "login": login, "display_name": login, "avatar": "", "game": ""}

    async def fetch_clip(broadcaster_id):
        return {"src": "/cache/clip.mp4", "title": "a clip", "duration": 4}

    monkeypatch.setattr(srv.tv.twitch, "user", user)
    monkeypatch.setattr(srv.tv, "fetch_clip", fetch_clip)
    await client.get("/raid/BigRaider?viewers=10")
    await client.get("/follow/AfterRaid")
    raid = await overlay.next("raid")
    assert raid["clip_pending"] is False                         # no clips on the overlay by default
    assert await tv.next("clip", timeout=3)                      # the TV is now playing the clip...
    t0 = time.monotonic()
    follow = await overlay.next("follow", timeout=3)             # ...and the overlay has already moved on
    assert follow and time.monotonic() - t0 < 2
    status = await (await client.get("/status")).json()
    assert status["showing"] == "clip" and status["queued"] == 1  # the follow still waits on the TV


async def test_overlay_clips_setting(client, srv, tv, overlay, monkeypatch):
    srv.S.update({"twitch_client_id": "id", "twitch_client_secret": "secret", "overlay_clips": True})

    async def user(login):
        return {"id": "42", "login": login, "display_name": login, "avatar": "", "game": ""}

    async def fetch_clip(broadcaster_id):
        return {"src": "/cache/clip.mp4", "title": "a clip", "duration": 0.2}

    monkeypatch.setattr(srv.tv.twitch, "user", user)
    monkeypatch.setattr(srv.tv, "fetch_clip", fetch_clip)
    await client.get("/shoutout/Streamer")
    assert (await overlay.next("shoutout"))["clip_pending"] is True
    assert await overlay.next("clip", timeout=3)


async def test_logo_clears_both_or_one(client, srv, tv, overlay):
    srv.S.data.update({"follow_seconds": 5, "overlay_seconds": 5})
    await client.get("/follow/One")
    await client.get("/follow/Two")
    await tv.next("follow"); await overlay.next("follow")
    r = await client.get("/logo?screen=overlay")
    assert (await r.json())["cleared"] == ["overlay"]
    assert await overlay.next("logo", timeout=2)
    status = await (await client.get("/status")).json()
    assert status["queued_overlay"] == 0 and status["queued"] == 1    # the TV kept its queue
    r = await client.get("/logo")
    assert (await r.json())["cleared"] == ["tv", "overlay"]
    assert (await (await client.get("/status")).json())["queued"] == 0


async def test_lights_only_follow_the_tv(srv, client, tv, overlay, aiohttp_server):
    calls = []

    async def record(request):
        calls.append(request.path)
        return web.Response(text="ok")

    fake = web.Application()
    fake.router.add_get("/{tail:.*}", record)
    lights = await aiohttp_server(fake)
    base = f"http://127.0.0.1:{lights.port}"
    srv.S.update({"govee_color_url": base + "/color/{hex}", "govee_reset_url": base + "/default",
                  "colors": {"follow": "#123456"}, "routes": {"follow": "overlay"}})
    await client.get("/follow/OverlayOnly")
    await overlay.next("follow")
    await overlay.next("logo", timeout=3)
    await asyncio.sleep(0.3)
    assert calls == []                                           # an overlay-only alert leaves the room alone


async def test_welcome_and_hype_follow_their_routes(client, srv, tv, overlay):
    srv.S.update({"routes": {"welcome": "overlay", "hype": "tv"}})
    await client.get("/welcome/Newbie")
    assert await overlay.next("welcome", timeout=2)
    assert await tv.next("welcome", timeout=1) is None
    await client.get("/hypetrain/start?level=1&percent=10")
    assert await tv.next("hype", timeout=2)
    assert await overlay.next("hype", timeout=1) is None


async def test_overlay_settings_validation_and_broadcast(client, srv, overlay):
    bad = [{"overlay_position": "middle"}, {"overlay_scale": 5}, {"overlay_opacity": 0},
           {"overlay_seconds": 100}, {"routes": {"follow": "fridge"}}]
    for body in bad:
        r = await client.post("/api/settings", json=body)
        assert r.status == 400, body
    r = await client.post("/api/settings", json={"overlay_position": "top-right", "overlay_scale": 1.5})
    assert r.status == 200
    ev = await overlay.next("logo_src", timeout=2)               # the overlay hears about it at once
    assert ev["overlay"]["position"] == "top-right" and ev["overlay"]["scale"] == 1.5
    srv.S.update({"routes": {"gigantify": "tv", "raid": "both"}})
    assert srv.S["routes"] == {}                                 # defaults aren't stored


async def test_old_settings_file_and_backup_still_load(client, srv, tmp_path):
    # a 1.4 settings file: none of the 1.5 keys
    old = {"card_seconds": 9, "theme": "halloween", "texts": {"raid.title": "INVASION!"}}
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(old), "utf-8")
    loaded = srv.Settings(path)
    assert loaded["card_seconds"] == 9 and loaded["routes"] == {} and loaded["overlay_seconds"] == 6.0
    assert loaded["overlay_position"] == "bottom-left" and loaded["overlay_clips"] is False
    # a 1.4 backup restores cleanly and leaves the new settings at their defaults
    backup = {"vibe_tv_backup": 1, "version": "1.4", "settings": {**srv.S.data, **old}}
    for k in ("routes", "overlay_position", "overlay_scale", "overlay_opacity", "overlay_seconds", "overlay_clips"):
        backup["settings"].pop(k)
    for k in ("card_seconds", "raid_seconds", "message_seconds", "follow_seconds", "gift_seconds", "sub_seconds",
              "bits_seconds", "welcome_seconds", "streak_seconds", "modiversary_seconds", "gigantify_seconds"):
        backup["settings"][k] = srv.SCHEMA[k][1]
    srv.S.update({"routes": {"follow": "overlay"}, "overlay_position": "top-right"})
    r = await client.post("/api/restore", json=backup)
    assert r.status == 200, await r.text()
    # the backup had no opinion on the new settings, so they stay as they were
    assert srv.S["theme"] == "halloween" and srv.S["routes"] == {"follow": "overlay"}
    assert srv.S["overlay_position"] == "top-right"





async def test_overlay_page_is_served(client):
    r = await client.get("/overlay")
    assert r.status == 200
    html = await r.text()
    assert "background: transparent" in html and "/static/shared.js" in html
