"""1.4: sub tiers, watch streaks, modiversaries, gigantified emotes, request log."""
import asyncio

from aiohttp import web


async def test_sub_tiers(client, srv, tv):
    base = srv.S["sub_seconds"]
    await client.get("/sub/Basic?tier=prime")
    ev = await tv.next("sub")
    assert ev["tier_level"] == 1 and "banner" not in ev["text"] and ev["card_seconds"] == base
    await client.get("/sub/Silver?tier=2000")
    ev = await tv.next("sub")
    assert ev["tier_level"] == 2 and ev["text"]["banner"] == "TIER 2" and ev["card_seconds"] == base + 2
    await client.get("/sub/Gold/tier3")                          # tier in the path works too
    ev = await tv.next("sub")
    assert ev["tier_level"] == 3 and ev["text"]["banner"] == "TIER 3" and ev["card_seconds"] == base + 4
    await client.get("/resub/Loyal?months=6&tier=Tier%203")      # "Tier 3" as MixItUp may write it
    ev = await tv.next("resub")
    assert ev["tier_level"] == 3 and ev["text"]["title"] == "6 MONTHS!"


async def test_tier3_uses_its_own_light_url(srv, client, tv, aiohttp_server):
    calls = []

    async def record(request):
        calls.append(request.path)
        return web.Response(text="ok")

    fake = web.Application()
    fake.router.add_get("/{tail:.*}", record)
    lights = await aiohttp_server(fake)
    base = f"http://127.0.0.1:{lights.port}"
    srv.S.update({"govee_color_url": base + "/color/{hex}", "govee_tier3_url": base + "/sparkle/{hex}/12",
                  "govee_reset_url": base + "/default", "colors": {"sub": "#112233"}})
    await client.get("/sub/Gold?tier=3")
    await tv.next("sub")
    await tv.next("logo", timeout=8)
    await asyncio.sleep(0.2)
    assert calls == ["/sparkle/112233/12", "/default"]


async def test_watch_streak(client, tv):
    await client.get("/streak/Loyal?count=12&message=hi")
    ev = await tv.next("streak")
    assert ev["count"] == 12 and ev["text"]["title"] == "12-STREAM STREAK!" and ev["text"]["message"] == "hi"


async def test_modiversary(client, srv, tv):
    await client.get("/modiversary/Guardian?years=2")
    ev = await tv.next("modiversary")
    assert ev["text"]["title"] == "2 YEARS OF MODDING" and ev["color"] == "00ad03"   # mod green by default
    await tv.next("logo", timeout=8)
    await client.get("/modiversary/Newbie?months=18")
    assert (await tv.next("modiversary"))["text"]["title"] == "18 MONTHS OF MODDING"
    await tv.next("logo", timeout=8)
    await client.get("/modiversary/Vet?months=24")
    assert (await tv.next("modiversary"))["text"]["title"] == "2 YEARS OF MODDING"
    assert srv.duration_text(years=1) == "1 YEAR" and srv.duration_text(months=1) == "1 MONTH"


async def test_gigantify(client, tv):
    assert (await client.get("/gigantify/Fan")).status == 400       # needs an emote
    await client.get("/gigantify/Fan?emote=emotesv2_0123456789abcdef")
    ev = await tv.next("gigantify")
    assert ev["emote"]["url"].endswith("/emotesv2_0123456789abcdef/default/dark/3.0")
    await client.get("/gigantify/Fan?emote=https://example.com/e.gif")
    assert (await tv.next("gigantify"))["emote"]["url"] == "https://example.com/e.gif"
    await client.get("/gigantify/Fan?emote=MadeUpEmote")             # no Twitch keys: shown as text
    ev = await tv.next("gigantify")
    assert ev["emote"] == {"url": "", "name": "MadeUpEmote"} and ev["text"]["caption"] == "Fan gigantified MadeUpEmote"


async def test_gigantify_finds_names_on_twitch(client, srv, tv, monkeypatch):
    srv.S.update({"twitch_client_id": "id", "twitch_client_secret": "secret", "twitch_channel": "mychannel"})

    async def emotes(broadcaster_id=None):
        return {"MyEmote": "emotesv2_abc12345"} if broadcaster_id else {"Kappa": "25"}

    async def user(login):
        return {"id": "999", "login": login, "display_name": login, "avatar": "", "game": ""} if login == "mychannel" else None

    monkeypatch.setattr(srv.tv.twitch, "emotes", emotes)
    monkeypatch.setattr(srv.tv.twitch, "user", user)
    await client.get("/gigantify/fan?emote=MyEmote")
    ev = await tv.next("gigantify")
    assert ev["emote"]["id"] == "emotesv2_abc12345" and ev["emote"]["name"] == "MyEmote"
    await client.get("/gigantify/fan?emote=Kappa")
    assert (await tv.next("gigantify"))["emote"]["id"] == "25"


async def test_request_log(client):
    await client.get("/follow/Pal?avatar=x")
    await client.get("/sub/bad$name")
    await client.get("/status")                                     # not an event: not logged
    log = (await (await client.get("/api/state")).json())["requests"]
    assert [r["url"] for r in log] == ["/sub/bad$name", "/follow/Pal?avatar=x"]
    assert log[0]["status"] == 400 and log[1]["status"] == 200
