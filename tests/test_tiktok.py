"""1.5: TikTok LIVE follows, subs and gifts, fed through the same queues and
routing as MixItUp's alerts. The TikTok connection itself is never opened
here: events are handed to the watcher directly, as TikTokLive would."""
import asyncio
import sys
from types import SimpleNamespace

import tiktok as tiktok_mod

ROSE = {"user": "rose_fan", "display": "Rose Fan", "avatar": ""}


async def test_follow_becomes_a_tagged_card_without_a_twitch_lookup(client, srv, tv, overlay, monkeypatch):
    srv.S.update({"twitch_client_id": "id", "twitch_client_secret": "secret"})

    async def no_twitch(login):
        raise AssertionError("TikTok people shouldn't be looked up on Twitch")

    monkeypatch.setattr(srv.tv.twitch, "user", no_twitch)
    assert srv.tiktok.follow({"user": "dance.queen", "display": "Dance Queen 💃", "avatar": ""}) == ["tv", "overlay"]
    card = await tv.next("follow")
    assert card["user"]["display_name"] == "Dance Queen 💃" and card["user"]["platform"] == "tiktok"
    assert (await overlay.next("follow"))["user"]["login"] == "dance.queen"


async def test_refollow_spam_is_shown_once(client, srv, tv):
    assert srv.tiktok.follow(dict(ROSE))
    assert srv.tiktok.follow(dict(ROSE)) is None
    assert srv.tiktok.counts["follow"] == 1


async def test_gift_combo_shows_once_with_the_total(client, srv, tv):
    for _ in range(4):                                   # tapping Rose again and again
        assert srv.tiktok.gift(dict(ROSE), "Rose", "", 1, count=_ + 1, streaking=True) is None
    assert srv.tiktok.gift(dict(ROSE), "Rose", "", 1, count=5) == ["tv", "overlay"]
    card = await tv.next("tiktok_gift")
    assert card["count"] == 5 and card["coins"] == 5 and card["gift"]["name"] == "Rose"
    assert card["text"]["title"] == "5× Rose!" and "5 coins" in card["text"]["sub"]
    assert await tv.next("tiktok_gift", timeout=1) is None


async def test_single_gift_title_and_smallest_gift_setting(client, srv, tv):
    srv.S.update({"tiktok_min_coins": 100})
    assert srv.tiktok.gift(dict(ROSE), "Rose", "", 1, count=10) is None      # 10 coins: too small
    srv.tiktok.gift(dict(ROSE), "Lion", "https://example.com/lion.png", 29999)
    card = await tv.next("tiktok_gift")
    assert card["text"]["title"] == "Lion!" and card["amount"] == 29999
    assert card["gift"]["image"] == "https://example.com/lion.png"


async def test_tiktok_gift_route_and_colour(client, srv, tv, overlay):
    srv.S.update({"routes": {"tiktok_gift": "overlay"}, "colors": {"tiktok_gift": "#fe2c55"}})
    srv.tiktok.gift(dict(ROSE), "Rose", "", 1)
    assert (await overlay.next("tiktok_gift"))["color"] == "fe2c55"
    assert await tv.next("tiktok_gift", timeout=1) is None


async def test_subscriptions_become_sub_or_resub(client, srv, tv):
    srv.tiktok.subscribe(dict(ROSE))
    assert (await tv.next("sub"))["user"]["platform"] == "tiktok"
    srv.tiktok.subscribe({"user": "loyal", "display": "Loyal", "avatar": ""}, months=6)
    card = await tv.next("resub")
    assert card["months"] == 6 and card["text"]["title"] == "6 MONTHS!"


async def test_test_endpoint(client, tv, overlay):
    r = await client.post("/api/test/tiktok?kind=gift&size=big&screen=overlay")
    assert (await r.json())["screens"] == ["overlay"]
    card = await overlay.next("tiktok_gift")
    assert card["gift"]["name"] == "Lion" and card["user"]["platform"] == "tiktok"
    assert (await client.post("/api/test/tiktok?kind=dance")).status == 400


async def test_settings_validation_and_secret_key(client, srv):
    assert (await client.post("/api/settings", json={"tiktok_username": "bad name!"})).status == 400
    assert (await client.post("/api/settings", json={"tiktok_min_coins": -1})).status == 400
    r = await client.post("/api/settings", json={"tiktok_username": "@My.Name_1", "tiktok_sign_key": "euler-key"})
    body = await r.json()
    assert body["settings"]["tiktok_username"] == "My.Name_1"
    assert "tiktok_sign_key" not in body["settings"] and body["settings"]["tiktok_sign_key_set"] is True
    backup = await (await client.get("/api/backup")).json()
    assert "tiktok_sign_key" not in backup["settings"]                     # secrets stay out of backups
    await client.post("/api/settings", json={"tiktok_sign_key": ""})       # blank keeps it
    assert srv.S["tiktok_sign_key"] == "euler-key"
    await client.post("/api/settings", json={"tiktok_sign_key": "-"})      # "-" clears it
    assert srv.S["tiktok_sign_key"] == ""


async def test_switching_on_and_off(client, srv, monkeypatch):
    runs = []

    async def fake_run(self, username, key):
        runs.append((username, key))
        self.set_state("live", "@" + username)
        await asyncio.sleep(3600)

    monkeypatch.setattr(tiktok_mod.TikTokWatcher, "run", fake_run)
    await client.post("/api/settings", json={"tiktok_enabled": True})
    state = await (await client.get("/api/state")).json()
    assert state["status"]["tiktok"]["state"] == "error"                   # no username yet
    await client.post("/api/settings", json={"tiktok_username": "MyLive"})
    await asyncio.sleep(0.05)
    assert runs == [("mylive", "")]
    assert (await (await client.get("/api/state")).json())["status"]["tiktok"]["state"] == "live"
    await client.post("/api/settings", json={"theme": "halloween"})        # unrelated change: no reconnect
    await asyncio.sleep(0.05)
    assert len(runs) == 1
    task = srv.tiktok.task
    await client.post("/api/settings", json={"tiktok_enabled": False})
    await asyncio.sleep(0.05)
    assert task.cancelled() and srv.tiktok.status()["state"] == "off"


async def test_missing_library_is_reported(srv, monkeypatch):
    monkeypatch.setitem(sys.modules, "TikTokLive", None)                   # import fails
    w = tiktok_mod.TikTokWatcher(srv.S, lambda ev: [])
    await w.run("someone", "")
    assert w.state == "error" and "isn't installed" in w.detail


def test_people_from_library_objects():
    u = SimpleNamespace(display_id="dance.queen", nickname="Dance Queen",
                        avatar_thumb=SimpleNamespace(url_list=["https://p16.example/a.webp", "https://p19.example/a.webp"]))
    assert tiktok_mod.person(u) == {"user": "dance.queen", "display": "Dance Queen", "avatar": "https://p16.example/a.webp"}
    assert tiktok_mod.person(SimpleNamespace(nickname="", display_id="", avatar_thumb=None))["user"] == "someone"


async def test_old_settings_have_tiktok_off(srv, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"card_seconds": 9}', "utf-8")
    loaded = srv.Settings(path)
    assert loaded["tiktok_enabled"] is False and loaded["tiktok_username"] == "" and loaded["tiktok_min_coins"] == 1.0
