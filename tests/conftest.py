"""Shared fixtures. The server reads its folders from the environment when
it's imported, so point them at a throwaway directory first."""
import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="vibetv-tests-"))
for _key in ("MEDIA_DIR", "CACHE_DIR", "CONFIG_DIR"):
    os.environ[_key] = str(_TMP / _key.lower())
os.environ.pop("ADMIN_PASSWORD", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pytest  # noqa: E402

import server  # noqa: E402

FAST = {  # keep cards short so the suite runs in seconds
    "card_seconds": 0.3, "raid_seconds": 0.3, "message_seconds": 0.3, "follow_seconds": 0.3,
    "gift_seconds": 0.3, "sub_seconds": 0.3, "bits_seconds": 0.3, "welcome_seconds": 0.3,
    "streak_seconds": 0.3, "modiversary_seconds": 0.3, "gigantify_seconds": 0.3, "overlay_seconds": 0.3,
}


SPOKEN = []   # what the fake voice was asked to say, newest last


async def fake_synth(text, voice, rate):
    """Stands in for Microsoft's voice: 0.3 s of "audio" (48 kbit/s = 6000 bytes a second)."""
    SPOKEN.append((text, voice, rate))
    return bytes(1800)


async def fake_voices():
    return [{"name": "en-US-EmmaMultilingualNeural", "locale": "en-US", "gender": "Female", "label": "Emma"},
            {"name": "en-GB-RyanNeural", "locale": "en-GB", "gender": "Male", "label": "Ryan"}]


@pytest.fixture
def srv(monkeypatch):
    """The server module with fresh settings and state for each test."""
    server.S.data = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, (_, v) in server.SCHEMA.items()}
    server.S.data.update(FAST)
    SPOKEN.clear()
    monkeypatch.setattr(server, "tv", server.TV())
    monkeypatch.setattr(server, "speaker", server.Speaker(
        server.S, server.tts_play, server.CACHE / "tts", synth=fake_synth, voices=fake_voices))
    monkeypatch.setattr(server, "tiktok", server.TikTokWatcher(
        server.S, lambda ev: server.tv.dispatch(ev, limit=True),
        chat=lambda who, text: server.speaker.say(text, who["display"], source="tiktok")))
    monkeypatch.setattr(server, "GIFT_WINDOW", 0.4)
    monkeypatch.setattr(server, "ADMIN_PASSWORD", "")
    for d in (server.MEDIA, server.CACHE, server.CONFIG):
        d.mkdir(parents=True, exist_ok=True)
    for f in server.MEDIA.iterdir():
        f.unlink()
    return server


@pytest.fixture
async def client(srv, aiohttp_client):
    return await aiohttp_client(srv.make_app())


class TVSocket:
    """A pretend TV: connects to /ws and waits for broadcast messages."""

    def __init__(self, ws):
        self.ws = ws

    async def next(self, *types, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                msg = await self.ws.receive_json(timeout=end - time.monotonic())
            except asyncio.TimeoutError:
                break
            if msg["type"] in types:
                return msg
        return None


@pytest.fixture
async def tv(client):
    ws = await client.ws_connect("/ws?preview=1")
    hello = await ws.receive_json()
    assert hello["type"] == "hello"
    sock = TVSocket(ws)
    sock.hello = hello
    yield sock
    await ws.close()


@pytest.fixture
async def overlay(client):
    """A pretend stream overlay (OBS Browser Source)."""
    ws = await client.ws_connect("/ws?screen=overlay&preview=1")
    hello = await ws.receive_json()
    assert hello["type"] == "hello" and hello["screen"] == "overlay"
    sock = TVSocket(ws)
    sock.hello = hello
    yield sock
    await ws.close()
