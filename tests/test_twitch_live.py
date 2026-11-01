"""1.9: Connect Twitch. Events straight from Twitch (EventSub) fill the
credits: mods and VIPs who chat, a new list when you go live, and, when
chosen, everyone who followed, subbed, gifted, cheered, raided... A fake
Twitch (login, subscriptions and the websocket) stands in for the real one."""
import asyncio
import json

from aiohttp import web

import twitch_live as tl

ME = {"broadcaster_user_id": "100", "broadcaster_user_login": "vibesbyvince"}


def chat(login, *badges, **more):
    return {**ME, "chatter_user_id": "7", "chatter_user_login": login, "chatter_user_name": login.title(),
            "badges": [{"set_id": b, "id": "1", "info": ""} for b in badges], "message": {"text": "hi"}, **more}


def notice(kind, login="fan", **obj):
    return {**ME, "chatter_user_id": "8", "chatter_user_login": login, "chatter_user_name": login.title(),
            "chatter_is_anonymous": False, "notice_type": kind, **obj}


async def settle():
    for _ in range(10):
        await asyncio.sleep(0.02)


# ── reading Twitch's messages ────────────────────────────────────────────

def test_chat_badges():
    assert tl.translate("channel.chat.message", chat("modone", "moderator", "subscriber")) == \
        [("seen", {"user": {"login": "modone", "name": "Modone", "avatar": ""}, "role": "mod"})]
    assert tl.translate("channel.chat.message", chat("buddy", "vip"))[0][1]["role"] == "vip"
    assert tl.translate("channel.chat.message", chat("regular", "subscriber")) == []
    assert tl.translate("channel.chat.message", chat("vibesbyvince", "broadcaster", "moderator")) == []   # not you
    shared = chat("othermod", "moderator", source_broadcaster_user_id="999")
    assert tl.translate("channel.chat.message", shared) == []                                             # another channel's chat


def test_chat_notifications():
    t = tl.translate
    assert t("channel.chat.notification", notice("sub", sub={"sub_tier": "2000", "is_prime": False}))[0] == \
        ("sub", {"user": {"login": "fan", "name": "Fan", "avatar": ""}, "tier": "2000"})
    assert t("channel.chat.notification", notice("sub", sub={"sub_tier": "1000", "is_prime": True}))[0][1]["tier"] == "prime"
    assert t("channel.chat.notification", notice("resub", resub={"cumulative_months": 14, "sub_tier": "1000"}))[0][1]["months"] == 14
    gift = t("channel.chat.notification", notice("sub_gift", "santa", sub_gift={"recipient_user_login": "elf", "recipient_user_name": "Elf"}))
    assert gift == [("gift", {"user": {"login": "santa", "name": "Santa", "avatar": ""},
                              "recipient": {"login": "elf", "name": "Elf", "avatar": ""}, "count": 1})]
    anon = notice("sub_gift", sub_gift={"recipient_user_login": "elf"}, chatter_is_anonymous=True)
    assert t("channel.chat.notification", anon)[0][1]["user"]["login"] == "anonymous"
    assert t("channel.chat.notification", notice("community_sub_gift", community_sub_gift={"total": 5})) == []
    raid = t("channel.chat.notification", notice("raid", raid={"user_login": "raider", "user_name": "Raider",
                                                               "viewer_count": 40, "profile_image_url": "https://example.com/r.png"}))
    assert raid == [("raid", {"user": {"login": "raider", "name": "Raider", "avatar": "https://example.com/r.png"}, "viewers": 40})]
    assert t("channel.chat.notification", notice("watch_streak", watch_streak={"streak_count": 9}))[0] == \
        ("streak", {"user": {"login": "fan", "name": "Fan", "avatar": ""}, "count": 9})
    assert t("channel.chat.notification", notice("shared_chat_resub")) == []


def test_follows_bits_hype_online():
    t = tl.translate
    assert t("channel.follow", {**ME, "user_login": "newpal", "user_name": "NewPal"}) == \
        [("follow", {"user": {"login": "newpal", "name": "NewPal", "avatar": ""}})]
    cheer = {**ME, "user_login": "cheery", "user_name": "Cheery", "type": "cheer", "bits": 500}
    assert t("channel.bits.use", cheer)[0] == ("bits", {"user": {"login": "cheery", "name": "Cheery", "avatar": ""}, "amount": 500})
    giga = {**ME, "user_login": "emotefan", "user_name": "EmoteFan", "type": "power_up", "bits": 100,
            "power_up": {"type": "gigantify_an_emote", "emote": {"id": "25", "name": "VibeHype"}}}
    assert t("channel.bits.use", giga)[0][1] == {"user": {"login": "emotefan", "name": "EmoteFan", "avatar": ""},
                                                 "emote_id": "25", "emote_name": "VibeHype"}
    effect = {**ME, "user_login": "x", "type": "power_up", "power_up": {"type": "message_effect"}}
    assert t("channel.bits.use", effect) == []
    assert t("channel.hype_train.progress", {**ME, "level": 3, "progress": 50, "goal": 100}) == [("hype", {"level": 3})]
    assert t("stream.online", {**ME, "type": "live"}) == [("online", {})]
    assert t("stream.online", {**ME, "type": "rerun"}) == []


# ── into the credits ─────────────────────────────────────────────────────

async def test_mods_and_vips_always_go_in(client, srv):
    await srv.twitch_live.handle("channel.chat.message", chat("modone", "moderator"))
    await srv.twitch_live.handle("channel.chat.message", chat("modone", "moderator"))
    await srv.twitch_live.handle("channel.chat.message", chat("buddy", "vip"))
    people = srv.session.data["people"]
    assert [p["login"] for p in people["mods"]] == ["modone"] and people["vips"][0]["name"] == "Buddy"


async def test_twitch_events_fill_the_credits_when_chosen(client, srv, tv):
    live = srv.twitch_live
    await live.handle("channel.follow", {**ME, "user_login": "newpal", "user_name": "NewPal"})
    assert srv.session.data["people"]["follows"] == []                   # default: credits come from the alerts
    srv.S.update({"credits_source": "twitch"})
    await live.handle("channel.follow", {**ME, "user_login": "newpal", "user_name": "NewPal"})
    await live.handle("channel.chat.notification", notice("resub", "loyal", resub={"cumulative_months": 14, "sub_tier": "2000"}))
    await live.handle("channel.chat.notification", notice("sub_gift", "santa", sub_gift={"recipient_user_login": "elf1", "recipient_user_name": "Elf1"}))
    await live.handle("channel.chat.notification", notice("sub_gift", "santa", sub_gift={"recipient_user_login": "elf2", "recipient_user_name": "Elf2"}))
    await live.handle("channel.bits.use", {**ME, "user_login": "cheery", "user_name": "Cheery", "type": "cheer", "bits": 300})
    await live.handle("channel.chat.notification", notice("raid", raid={"user_login": "raider", "user_name": "Raider", "viewer_count": 40}))
    await live.handle("channel.chat.notification", notice("watch_streak", "watcher", watch_streak={"streak_count": 9}))
    await live.handle("channel.bits.use", {**ME, "user_login": "emotefan", "user_name": "EmoteFan", "type": "power_up",
                                           "power_up": {"type": "gigantify_an_emote", "emote": {"id": "25", "name": "Kappa"}}})
    await live.handle("channel.hype_train.end", {**ME, "level": 4})
    people = srv.session.data["people"]
    assert people["follows"][0]["name"] == "NewPal"
    assert people["resubs"][0]["months"] == 14 and people["resubs"][0]["tier"] == "Tier 2"
    assert people["gifts"][0]["count"] == 2 and [r["login"] for r in people["gifts"][0]["to"]] == ["elf1", "elf2"]
    assert people["cheers"][0]["amount"] == 300 and people["raiders"][0]["viewers"] == 40
    assert people["streaks"][0]["count"] == 9 and people["gigantify"][0]["emotes"][0].endswith("/25/default/dark/3.0")
    assert srv.session.data["hype_level"] == 4
    # the MixItUp alerts still play, but don't add the same people twice
    await client.get("/follow/AlsoFromMixItUp")
    await client.get("/welcome/Newbie")                                 # first-timers still come from MixItUp
    assert await tv.next("follow")
    await settle()
    assert [p["login"] for p in people["follows"]] == ["newpal"] and people["first_chatters"][0]["login"] == "newbie"


async def test_going_live_starts_a_new_list(client, srv):
    await client.get("/credits/seen/OldMod?role=mod")
    srv.S.update({"credits_auto_reset": False})
    await srv.twitch_live.handle("stream.online", {**ME, "type": "live"})
    assert srv.session.data["people"]["mods"]
    srv.S.update({"credits_auto_reset": True})
    await srv.twitch_live.handle("stream.online", {**ME, "type": "live"})
    assert srv.session.data["people"]["mods"] == []


async def test_settings(client, srv):
    assert (await client.post("/api/settings", json={"credits_source": "youtube"})).status == 400
    assert (await client.post("/api/settings", json={"credits_source": "twitch"})).status == 200
    state = await (await client.get("/api/state")).json()
    assert state["status"]["twitch_live"]["state"] == "off" and state["status"]["twitch_live"]["account"] is None
    r = await (await client.post("/api/twitch/connect")).json()
    assert r["ok"] is False and "Client ID" in r["result"]              # keys first


# ── the whole thing, against a fake Twitch ───────────────────────────────

async def test_connect_and_listen(client, srv, aiohttp_server, monkeypatch):
    seen = {"token_calls": 0, "subs": [], "ws": None}

    async def device(request):
        form = await request.post()
        assert form["client_id"] == "cid" and "user:read:chat" in form["scopes"]
        return web.json_response({"device_code": "dev123", "user_code": "ABCD-EFGH", "verification_uri": "https://www.twitch.tv/activate?device-code=ABCD-EFGH",
                                  "expires_in": 60, "interval": 0})

    async def token(request):
        form = await request.post()
        seen["token_calls"] += 1
        assert form["client_secret"] == "sec"
        if form["grant_type"].endswith("device_code"):
            if seen["token_calls"] == 1:
                return web.json_response({"status": 400, "message": "authorization_pending"}, status=400)
            return web.json_response({"access_token": "user-token", "refresh_token": "r1", "expires_in": 14400})
        return web.json_response({"access_token": "new-token", "refresh_token": "r2", "expires_in": 14400})

    async def validate(request):
        assert request.headers["Authorization"].startswith("OAuth ")
        return web.json_response({"login": "vibesbyvince", "user_id": "100", "scopes": tl.SCOPES, "expires_in": 14000})

    async def subscribe(request):
        body = await request.json()
        assert request.headers["Authorization"] == "Bearer user-token" and body["transport"]["session_id"] == "sess-1"
        if body["type"].startswith("channel.hype_train") and body["version"] == "2":
            return web.json_response({"message": "version not supported"}, status=400)   # falls back to version 1
        seen["subs"].append((body["type"], body["version"]))
        return web.json_response({"data": [{}]}, status=202)

    async def websocket(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        seen["ws"] = ws
        await ws.send_json({"metadata": {"message_type": "session_welcome"},
                            "payload": {"session": {"id": "sess-1", "keepalive_timeout_seconds": 10}}})
        async for _ in ws:
            pass
        return ws

    fake = web.Application()
    fake.router.add_post("/oauth2/device", device)
    fake.router.add_post("/oauth2/token", token)
    fake.router.add_get("/oauth2/validate", validate)
    fake.router.add_post("/helix/eventsub/subscriptions", subscribe)
    fake.router.add_get("/ws", websocket)
    twitch = await aiohttp_server(fake)
    base = f"http://127.0.0.1:{twitch.port}"
    monkeypatch.setattr(tl, "AUTH_URL", base + "/oauth2")
    monkeypatch.setattr(tl, "HELIX_URL", base + "/helix")
    monkeypatch.setattr(tl, "EVENTSUB_URL", f"ws://127.0.0.1:{twitch.port}/ws")
    srv.S.update({"twitch_client_id": "cid", "twitch_client_secret": "sec"})

    async def no_lookup(login):          # the picture lookup (app keys) stays offline too
        return None

    monkeypatch.setattr(srv.tv.twitch, "user", no_lookup)
    r = await (await client.post("/api/twitch/connect")).json()
    assert r["ok"] and r["code"] == "ABCD-EFGH"
    for _ in range(100):                                                # you approve at twitch.tv/activate...
        if srv.twitch_live.state == "live":
            break
        await asyncio.sleep(0.05)
    status = srv.twitch_live.status()
    assert status["state"] == "live" and status["account"] == "vibesbyvince" and status["login"] is None
    assert ("channel.chat.message", "1") in seen["subs"] and ("channel.hype_train.begin", "1") in seen["subs"]
    assert len(seen["subs"]) == 8
    saved = json.loads((srv.CONFIG / "twitch_login.json").read_text("utf-8"))
    assert saved["user_id"] == "100" and saved["refresh_token"] == "r1"
    assert "twitch_login" not in json.dumps(await (await client.get("/api/backup")).json())   # never in backups

    # a mod chats: into the credits
    await seen["ws"].send_json({"metadata": {"message_type": "notification", "subscription_type": "channel.chat.message"},
                                "payload": {"event": chat("modone", "moderator")}})
    for _ in range(50):
        if srv.session.data["people"]["mods"]:
            break
        await asyncio.sleep(0.05)
    assert srv.session.data["people"]["mods"][0]["login"] == "modone"

    # an old login is renewed with the refresh token
    srv.twitch_live.auth["expires"] = 0
    assert await srv.twitch_live.token() == "new-token"

    await client.post("/api/twitch/disconnect")
    assert not (srv.CONFIG / "twitch_login.json").exists() and srv.twitch_live.status()["account"] is None
