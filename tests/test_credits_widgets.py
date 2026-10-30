"""1.8: end credits (everyone from this stream) and the TikTok widgets
(likes, top likers, top gifters)."""
import asyncio

from conftest import TVSocket


async def credits_page(client):
    ws = await client.ws_connect("/ws?screen=credits&preview=1")
    assert (await ws.receive_json())["type"] == "hello"
    sock = TVSocket(ws)
    sock.first = await ws.receive_json()
    return sock


async def wait_for(check, timeout=3.0):
    end = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < end:
        if check():
            return True
        await asyncio.sleep(0.05)
    return False


# ── the credits list ─────────────────────────────────────────────────────

async def test_alerts_are_remembered_for_the_credits(client, srv, tv):
    await client.get("/follow/NewPal?avatar=https://example.com/pal.png")
    await client.get("/sub/GoldSub?tier=3")
    await client.get("/resub/Loyal?months=12")
    await client.get("/bits/Cheery?amount=100")
    await client.get("/bits/Cheery?amount=400")
    await client.get("/raid/Raider?viewers=40&clip=0")
    await client.get("/streak/Watcher?count=9")
    await client.get("/welcome/Newbie")
    await client.get("/gift/Santa?to=elf1,elf2&count=2")
    await client.get("/gigantify/EmoteFan?emote=25")
    await client.get("/hypetrain/start?level=3")
    people = srv.session.data["people"]
    assert await wait_for(lambda: people["gifts"] and people["gigantify"] and people["first_chatters"])
    assert people["follows"][0] == {"login": "newpal", "name": "NewPal", "avatar": "https://example.com/pal.png"}
    assert people["subs"][0]["tier"] == "Tier 3" and people["resubs"][0]["months"] == 12
    assert people["cheers"][0]["amount"] == 500                          # cheers add up, one entry
    assert people["raiders"][0]["viewers"] == 40 and people["streaks"][0]["count"] == 9
    assert [r["login"] for r in people["gifts"][0]["to"]] == ["elf1", "elf2"] and people["gifts"][0]["count"] == 2
    assert people["gigantify"][0]["emotes"][0].endswith("/25/default/dark/3.0")
    snap = srv.session.snapshot()
    assert snap["hype_level"] == 3 and snap["stats"]["bits"] == 500 and snap["stats"]["subs"] == 2


async def test_tests_and_tiktok_are_left_out(client, srv, tv):
    await client.get("/follow/Tester?test=1")
    await client.get("/hypetrain/start?level=5&test=1")
    await client.post("/api/test/tiktok?kind=follow")
    srv.tiktok.follow({"user": "tikfan", "display": "TikFan", "avatar": ""})
    await client.get("/follow/RealOne")
    assert await wait_for(lambda: srv.session.data["people"]["follows"])
    await asyncio.sleep(0.2)
    assert [p["login"] for p in srv.session.data["people"]["follows"]] == ["realone"]
    assert srv.session.data["hype_level"] == 0


async def test_mods_vips_reset_and_saved(client, srv):
    r = await client.get("/credits/seen/ModOne?role=mod&avatar=https://example.com/m.png")
    assert (await r.json())["count"] == 1
    await client.get("/credits/seen/ModOne?role=mod")                  # once per stream
    await client.get("/credits/seen/BestBuddy?role=vip")
    assert (await client.get("/credits/seen/X?role=king")).status == 400
    people = srv.session.data["people"]
    assert [p["name"] for p in people["mods"]] == ["ModOne"] and people["mods"][0]["avatar"] == "https://example.com/m.png"
    assert people["vips"][0]["name"] == "BestBuddy"
    again = srv.Session(srv.CONFIG / "session.json")                    # survives a restart
    assert again.data["people"]["mods"][0]["login"] == "modone"
    await client.get("/credits/reset")
    assert srv.session.data["people"]["mods"] == []


async def test_credits_page_gets_the_list_and_play(client, srv):
    await client.get("/credits/seen/ModOne?role=mod")
    page = await credits_page(client)
    assert page.first["type"] == "credits_data" and page.first["data"]["people"]["mods"][0]["name"] == "ModOne"
    await client.get("/follow/Later")
    update = await page.next("credits_data", timeout=3)               # kept up to date for the next roll
    assert update["data"]["people"]["follows"][0]["name"] == "Later"
    r = await (await client.get("/credits/play")).json()
    assert r["pages"] == 0                                              # previews (like this one) aren't counted...
    assert await page.next("credits_play", timeout=2)                   # ...but they still play
    await page.ws.close()


async def test_credits_settings(client, srv):
    for bad in ({"credits_background": "neon"}, {"credits_title": "x" * 81}, {"credits_speed": 9}):
        assert (await client.post("/api/settings", json=bad)).status == 400, bad
    r = await client.post("/api/settings", json={"credits_sections": {"mods": True, "stats": False, "nope": False},
                                                 "credits_title": "GG everyone!"})
    assert r.status == 200 and srv.S["credits_sections"] == {"stats": False}
    info = srv.credits_info()
    assert "stats" not in info["sections"] and info["sections"][0] == "mods" and info["title"] == "GG everyone!"
    assert (await client.get("/credits")).status == 200


# ── TikTok widgets ───────────────────────────────────────────────────────

FAN = {"user": "dancequeen", "display": "DanceQueen", "avatar": "https://example.com/dq.webp"}


async def test_likes_and_top_likers(client, srv):
    srv.tiktok.like(FAN, 15, total=1000)
    srv.tiktok.like({"user": "pal", "display": "Pal", "avatar": ""}, 40)
    srv.tiktok.like(FAN, 30)
    snap = srv.tiktok_stats.snapshot()
    assert snap["likes"] == 1070                                        # TikTok's total, plus what came after
    assert snap["likers"][0] == {"name": "DanceQueen", "avatar": "https://example.com/dq.webp", "likes": 45}
    assert [p["name"] for p in snap["likers"]] == ["DanceQueen", "Pal"]


async def test_every_gift_counts_for_top_gifters(client, srv):
    srv.S.update({"tiktok_min_coins": 100})
    srv.tiktok.gift(FAN, "Rose", "", 1, count=5)                         # too small for an alert...
    srv.tiktok.gift(FAN, "Rose", "", 1, count=3, streaking=True)         # ...a combo still going isn't counted yet
    srv.tiktok.gift({"user": "whale", "display": "Whale", "avatar": ""}, "Lion", "", 29999)
    gifters = srv.tiktok_stats.snapshot()["gifters"]
    assert [(g["name"], g["coins"]) for g in gifters] == [("Whale", 29999), ("DanceQueen", 5)]


async def test_new_live_starts_over_and_reset(client, srv):
    srv.tiktok_stats.new_live("room-1")
    srv.tiktok.like(FAN, 10)
    srv.tiktok_stats.new_live("room-1")                                 # a reconnect to the same live
    assert srv.tiktok_stats.data["likes"] == 10
    again = srv.TikTokStats(srv.CONFIG / "tiktok_stats.json")           # saved for a restart
    assert again.data["room"] == "room-1"
    srv.tiktok_stats.new_live("room-2")                                 # a new live
    assert srv.tiktok_stats.data["likes"] == 0
    srv.tiktok.like(FAN, 10)
    await client.get("/tiktok/reset")
    assert srv.tiktok_stats.snapshot()["likers"] == []


async def test_widget_pages_get_live_numbers(client, srv):
    for kind in ("likes", "likers", "gifters", "combined"):
        assert (await client.get(f"/tiktok/{kind}")).status == 200
    assert (await client.get("/tiktok/nope")).status == 404
    ws = await client.ws_connect("/ws?screen=tiktok&preview=1")
    hello = await ws.receive_json()
    assert hello["widgets"] == {"count": 5, "layout": "column", "scale": 1.0, "opacity": 0.85, "goal": 0, "hide_offline": True}
    page = TVSocket(ws)
    assert (await page.next("tiktok_stats", timeout=2))["likes"] == 0
    for _ in range(20):                                                 # a flood of likes...
        srv.tiktok.like(FAN, 5)
    first = await page.next("tiktok_stats", timeout=2)
    assert first["likes"] == 100 and first["likers"][0]["name"] == "DanceQueen"
    assert await page.next("tiktok_stats", timeout=0.6) is None          # ...is one update, not twenty
    srv.tiktok.set_state("live")
    assert (await page.next("tiktok_stats", timeout=2))["live"] is True
    await ws.close()


async def test_widget_settings_and_test_button(client, srv):
    for bad in ({"tiktok_widget_layout": "grid"}, {"tiktok_widget_count": 20}, {"tiktok_widget_scale": 5}):
        assert (await client.post("/api/settings", json=bad)).status == 400, bad
    r = await client.post("/api/settings", json={"tiktok_widget_layout": "row", "tiktok_like_goal": 5000})
    assert r.status == 200 and srv.widget_info()["goal"] == 5000
    r = await (await client.post("/api/test/tiktok?kind=likes")).json()
    assert r["likes"] > 0 and len(srv.tiktok_stats.snapshot()["likers"]) == 3
    await client.post("/api/test/tiktok?kind=gift&size=big")
    assert srv.tiktok_stats.snapshot()["gifters"][0]["coins"] == 29999


async def test_old_settings_load_with_defaults(srv, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"card_seconds": 9}', "utf-8")
    old = srv.Settings(path)
    assert old["credits_sections"] == {} and old["credits_background"] == "dark"
    assert old["tiktok_widget_count"] == 5.0 and old["tiktok_widget_hide_offline"] is True
