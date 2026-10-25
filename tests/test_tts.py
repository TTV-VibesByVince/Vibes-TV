"""1.6: text to speech. TikTok chat and /tts are read aloud one at a time,
on the overlay by default, with filters against trolls. A fake voice
stands in for Microsoft's (see conftest.py), so nothing goes online."""
import asyncio

from conftest import SPOKEN


def tts_on(srv, **more):
    srv.S.update({"tts_enabled": True, "tts_cooldown": 0, **more})


async def test_off_by_default(client, overlay):
    r = await (await client.get("/tts?text=hello&from=Pal")).json()
    assert r == {"ok": False, "skipped": "text to speech is off"}
    assert await overlay.next("tts", timeout=1) is None


async def test_reads_on_the_overlay_by_default(client, srv, tv, overlay):
    tts_on(srv)
    r = await (await client.get("/tts?text=hello%20chat&from=Pal")).json()
    assert r["ok"] is True
    msg = await overlay.next("tts", timeout=3)
    assert msg["text"] == "hello chat" and msg["from"] == "Pal" and msg["src"].startswith("/cache/tts/")
    assert msg["seconds"] == 0.3 and msg["volume"] == 1.0 and msg["show"] is True
    assert SPOKEN[-1] == ("Pal says hello chat", "en-US-EmmaMultilingualNeural", 0.0)
    assert await tv.next("tts", timeout=1) is None                     # not on the TV unless routed there
    assert await overlay.next("tts_end", timeout=2)
    audio = await client.get(msg["src"])
    assert audio.status == 200 and len(await audio.read()) == 1800


async def test_one_at_a_time_and_skip(client, srv, overlay):
    tts_on(srv)
    for word in ("one", "two"):
        await client.get(f"/tts?text={word}&from=A{word}")
    first = await overlay.next("tts", timeout=3)
    assert first["text"] == "one"
    await client.get("/tts/skip")
    assert await overlay.next("tts_end", timeout=1)                    # cut short
    assert (await overlay.next("tts", timeout=2))["text"] == "two"


async def test_filters(client, srv, overlay):
    tts_on(srv, tts_blocked="badword, worse word", tts_cooldown=60, tts_max_chars=20)
    say = srv.speaker.say
    assert say("!uptime", "A") == (False, "a command")
    assert say("go to cheap-followers.com now", "A") == (False, "has a link")
    assert say("check https://example.com", "A") == (False, "has a link")
    assert say("you BADWORD", "A") == (False, "has a blocked word")
    assert say("a worse word here", "A") == (False, "has a blocked word")
    assert say("first class stream", "A") == (True, None)               # "ass" isn't blocked inside "class"
    assert say("again so soon", "A") == (False, "cooldown")
    assert say("I have a lot to say about this stream today", "B") == (True, None)
    await overlay.next("tts", timeout=3)
    second = await overlay.next("tts", timeout=3)
    assert len(second["text"]) <= 20 and second["text"] == "I have a lot to say"   # cut at a word


async def test_busy_chat_keeps_only_the_newest(srv):
    tts_on(srv)
    for i in range(9):
        srv.speaker.say(f"message {i}", f"P{i}")
    assert [m["text"] for m in srv.speaker.waiting] == [f"message {i}" for i in range(4, 9)]


async def test_tiktok_chat_is_read(client, srv, overlay):
    tts_on(srv)
    srv.tiktok.chat({"user": "dancer", "display": "Dancer", "avatar": ""}, "love this song")
    msg = await overlay.next("tts", timeout=3)
    assert msg["source"] == "tiktok" and msg["from"] == "Dancer"
    srv.S.update({"tts_tiktok_chat": False})
    assert srv.tiktok.chat({"user": "dancer2", "display": "Dancer2", "avatar": ""}, "hi") == (False, "reading TikTok chat is off")


async def test_routing_and_logo_stops_it(client, srv, tv, overlay):
    tts_on(srv, routes={"tts": "tv"})
    srv.S.data["tts_cooldown"] = 0
    await client.get("/tts?text=on%20the%20tv&from=Pal")
    assert await tv.next("tts", timeout=3)
    for i in range(3):
        srv.speaker.say(f"more {i}", f"Q{i}")
    await client.get("/logo")                                          # clears what's waiting, stops the voice
    assert await tv.next("tts_end", timeout=1)
    await asyncio.sleep(0.2)
    assert not srv.speaker.waiting


async def test_settings_and_validation(client, srv):
    for bad in ({"tts_voice": "robot"}, {"tts_format": "{name} said something"}, {"tts_rate": 500},
                {"tts_volume": 2}, {"tts_max_chars": 5}):
        assert (await client.post("/api/settings", json=bad)).status == 400, bad
    r = await client.post("/api/settings", json={"tts_voice": "en-GB-RyanNeural", "tts_format": "[{name}: ]{message}"})
    assert r.status == 200
    assert (await client.post("/api/settings", json={"tts_voice": ""})).status == 200   # page not ready: keep it
    assert srv.S["tts_voice"] == "en-GB-RyanNeural"
    tts_on(srv)
    srv.speaker.say("no name here")
    await asyncio.sleep(0.1)
    assert SPOKEN[-1][0] == "no name here"


async def test_voices_and_preview(client):
    r = await (await client.get("/api/tts/voices")).json()
    assert r["ok"] and r["voices"][1]["name"] == "en-GB-RyanNeural"
    r = await client.get("/api/tts/preview?voice=en-GB-RyanNeural&rate=20&text=testing")
    assert r.status == 200 and r.content_type == "audio/mpeg"
    assert SPOKEN[-1] == ("testing", "en-GB-RyanNeural", 20.0)
    assert (await client.get("/api/tts/preview?voice=<script>")).status == 400


async def test_status_and_old_settings(client, srv, tmp_path):
    state = await (await client.get("/api/state")).json()
    assert state["status"]["tts"]["enabled"] is False and "tts" in state["route_events"]
    assert state["route_defaults"]["tts"] == "overlay"
    path = tmp_path / "settings.json"
    path.write_text('{"card_seconds": 9}', "utf-8")
    old = srv.Settings(path)
    assert old["tts_enabled"] is False and old["tts_format"] == "{name} says {message}"
