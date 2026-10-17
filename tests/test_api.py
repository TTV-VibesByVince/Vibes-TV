"""End to end: MixItUp URLs in, TV websocket messages out."""
import asyncio
import json

from aiohttp import FormData, web


async def test_status_and_pages(client, srv):
    r = await client.get("/status")
    body = await r.json()
    assert body["version"] == srv.VERSION
    for path in ("/", "/tv", "/admin", "/favicon.ico"):
        assert (await client.get(path)).status == 200


async def test_bad_requests(client):
    assert (await client.get("/shoutout/bad$name")).status == 400
    assert (await client.get("/message")).status == 400
    assert (await client.get("/bits/someone")).status == 400     # amount is required
    assert (await client.get("/hypetrain/derail")).status == 404


async def test_shoutout_and_raid(client, tv):
    await client.get("/shoutout/CoolStreamer?game=Minecraft&clip=0")
    ev = await tv.next("shoutout")
    assert ev["user"]["display_name"] == "CoolStreamer"          # capitals kept without Twitch keys
    assert ev["text"]["sub"] == "Last seen playing Minecraft"
    assert await tv.next("logo")
    await client.get("/raid/Raider?viewers=42&clip=0")
    ev = await tv.next("raid")
    assert ev["viewers"] == 42 and ev["text"]["title"] == "RAID!"


async def test_follow_sub_resub_bits(client, tv):
    await client.get("/follow/Pal")
    assert (await tv.next("follow"))["text"]["title"] == "THANKS FOR THE FOLLOW!"
    await client.get("/sub/NewSub?tier=1000")
    assert (await tv.next("sub"))["text"]["sub"] == "Tier 1 sub"
    await client.get("/resub/Loyal?months=24&tier=prime&message=Still%20here")
    ev = await tv.next("resub")
    assert ev["text"]["title"] == "24 MONTHS!" and ev["text"]["message"] == "Still here"
    await client.get("/bits/Cheerer?amount=1500")
    ev = await tv.next("bits")
    assert ev["text"]["title"] == "1,500 BITS!" and ev["amount"] == 1500


async def test_welcome_skips_the_queue(client, srv, tv):
    srv.S.data["raid_seconds"] = 3
    await client.get("/raid/Raider?clip=0")
    await tv.next("raid")
    await client.get("/welcome/FirstTimer")
    ev = await tv.next("welcome", timeout=2)                     # arrives while the raid is still on
    assert ev and ev["user"]["display_name"] == "FirstTimer"


async def test_gifts_are_batched(client, tv):
    await client.get("/giftbomb/Santa?count=3")
    for name in ("ann", "bob", "bob", "cat"):                    # duplicate bob is ignored
        await client.get(f"/gift/Santa?to={name}")
    ev = await tv.next("gift")
    assert ev["count"] == 3 and [p["display_name"] for p in ev["recipients"]] == ["ann", "bob", "cat"]
    assert ev["text"]["title"] == "GIFTED 3 SUBS"


async def test_logo_cancels_pending_gifts_and_hype(client, tv):
    await client.get("/hypetrain/start?level=1&percent=10")
    await tv.next("hype")
    await client.get("/gift/Grinch?to=who")
    await client.get("/logo")
    ev = await tv.next("hype")
    assert ev["state"] is None
    assert await tv.next("gift", timeout=1) is None


async def test_hype_train(client, tv):
    await client.get("/hypetrain/start?level=1&progress=200&goal=1000")
    ev = await tv.next("hype")
    assert ev["state"]["percent"] == 20 and ev["banner"]["kind"] == "start"
    await client.get("/hypetrain/progress?level=1&percent=65")
    ev = await tv.next("hype")
    assert ev["state"]["percent"] == 65 and ev["banner"] is None
    await client.get("/hypetrain/progress?level=2&percent=5")
    assert (await tv.next("hype"))["banner"]["text"] == "LEVEL 2!"
    late = await client.ws_connect("/ws?preview=1")              # a TV that joins mid-train
    await late.receive_json()
    assert (await late.receive_json())["state"]["level"] == 2
    await late.close()
    await client.get("/hypetrain/end")
    ev = await tv.next("hype")
    assert ev["state"] is None and ev["banner"]["kind"] == "end"


async def test_theme_change_reaches_tvs(client, tv):
    assert tv.hello["theme"]["id"] == "default"
    r = await client.post("/api/settings", json={"theme": "halloween"})
    assert r.status == 200
    ev = await tv.next("logo_src")
    assert ev["theme"]["id"] == "halloween" and ev["theme"]["float"] == "bat"


async def test_backup_and_restore(client, srv):
    for key in ("card_seconds", "raid_seconds", "message_seconds", "follow_seconds",   # real timings:
                "gift_seconds", "sub_seconds", "bits_seconds", "welcome_seconds",      # restore checks ranges
                "streak_seconds", "modiversary_seconds", "gigantify_seconds"):
        srv.S.data[key] = srv.SCHEMA[key][1]
    await client.post("/api/settings", json={"texts": {"raid.title": "INVASION!"}, "theme": "halloween",
                                             "twitch_client_secret": "shh"})
    r = await client.get("/api/backup")
    assert "attachment" in r.headers["Content-Disposition"]
    backup = await r.json()
    assert "shh" not in json.dumps(backup)
    assert (await (await client.get("/api/backup?secrets=1")).json())["settings"]["twitch_client_secret"] == "shh"
    await client.post("/api/settings", json={"texts": {}, "theme": "default"})
    backup["settings"]["logo"] = "missing.mp4"
    r = await client.post("/api/restore", json=backup)
    body = await r.json()
    assert r.status == 200 and body["notes"]                     # warns about the missing logo
    assert srv.S["texts"]["raid.title"] == "INVASION!" and srv.S["theme"] == "halloween"
    assert (await client.post("/api/restore", json={"hello": 1})).status == 400


async def test_upload_and_delete_logo(client, srv):
    form = FormData()
    form.add_field("file", b"\x89PNG fake", filename="../../my logo!.png", content_type="image/png")
    r = await client.post("/api/media", data=form)
    assert r.status == 200 and (await r.json())["name"] == "my logo.png"
    form = FormData()
    form.add_field("file", b"MZ", filename="evil.exe")
    assert (await client.post("/api/media", data=form)).status == 400
    assert (await client.delete("/api/media/..%2Fserver.py")).status == 404
    assert (await client.delete("/api/media/my%20logo.png")).status == 200


async def test_admin_password(srv, monkeypatch, aiohttp_client):
    monkeypatch.setattr(srv, "ADMIN_PASSWORD", "letmein")
    c = await aiohttp_client(srv.make_app())
    assert (await c.get("/admin")).status == 401
    assert (await c.get("/api/state")).status == 401
    import base64
    ok = {"Authorization": "Basic " + base64.b64encode(b"x:letmein").decode()}
    assert (await c.get("/admin", headers=ok)).status == 200
    assert (await c.get("/tv")).status == 200                    # the TV and MixItUp URLs stay open
    assert (await c.get("/follow/Someone")).status == 200


async def test_lights_follow_the_card(srv, client, tv, aiohttp_server):
    calls = []

    async def record(request):
        calls.append(request.path)
        return web.Response(text="ok")

    fake = web.Application()
    fake.router.add_get("/{tail:.*}", record)
    lights = await aiohttp_server(fake)
    base = f"http://127.0.0.1:{lights.port}"
    srv.S.update({"govee_color_url": base + "/color/{hex}", "govee_reset_url": base + "/default",
                  "colors": {"follow": "#123456"}})
    await client.get("/follow/Pal")
    await tv.next("follow")
    await tv.next("logo")
    await asyncio.sleep(0.2)
    assert calls == ["/color/123456", "/default"]
