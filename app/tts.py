"""Text to speech for Vibe TV (optional, off by default).

Reads TikTok LIVE chat (and anything MixItUp sends to /tts) aloud with
Microsoft Edge's online neural voices, through edge-tts
(https://github.com/rany2/edge-tts, LGPL-3.0). edge-tts is unofficial and
needs no key; it's imported only when something is actually spoken.

Messages are read one at a time from their own short queue, so they never
hold up alerts. The server makes the audio file; the overlay (and/or the TV)
plays it.
"""
import asyncio
import collections
import hashlib
import logging
import re
import time
import uuid
from pathlib import Path

log = logging.getLogger("vibetv.tts")

BYTES_PER_SECOND = 6000     # edge-tts sends 48 kbit/s mono MP3
MAX_WAITING = 5             # unread messages kept; older ones are dropped when chat is busy
MAX_AGE = 60                # a message still waiting after this many seconds is dropped
KEEP_FILES = 600            # spoken audio files are deleted after this many seconds
LINK_RE = re.compile(r"(https?://|www\.)\S+|\b\S+\.(com|net|org|tv|gg|ly|io|me|co)\b(/\S*)?", re.I)
VOICE_RE = re.compile(r"^[a-z]{2,3}-[A-Za-z0-9]{2,8}(-[A-Za-z0-9]+)*Neural$")


def fill(template, **values):
    """{name} / {message} placeholders, and [optional parts] that only show
    when their placeholders have a value (same rules as the on-screen text)."""
    vals = {k: ("" if v is None else str(v)) for k, v in values.items()}

    def put(s):
        return re.sub(r"\{(\w+)\}", lambda m: vals.get(m.group(1), ""), s)

    def optional(m):
        names = re.findall(r"\{(\w+)\}", m.group(1))
        return put(m.group(1)) if all(vals.get(n) for n in names) else ""

    return re.sub(r"\s{2,}", " ", put(re.sub(r"\[([^\[\]]*)\]", optional, template))).strip()


def blocked_words(raw):
    return [w.strip().lower() for w in re.split(r"[,\n]", raw or "") if w.strip()]


async def edge_synth(text, voice, rate):
    """MP3 bytes for text, from Microsoft Edge's read-aloud service."""
    import edge_tts      # imported here: only needed once TTS is used
    audio = bytearray()
    async for chunk in edge_tts.Communicate(text, voice, rate=f"{int(rate):+d}%").stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    if not audio:
        raise RuntimeError("no audio came back")
    return bytes(audio)


async def edge_voices():
    import edge_tts
    return [{"name": v["ShortName"], "locale": v["Locale"], "gender": v.get("Gender", ""), "label": voice_label(v["ShortName"])}
            for v in await edge_tts.list_voices()]


def voice_label(short_name):
    """en-US-EmmaMultilingualNeural -> Emma Multilingual"""
    base = short_name.split("-", 2)[-1].removesuffix("Neural")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base)


class Speaker:
    """settings: the Settings object (tts_* keys).
    play(msg, screens_override): sends a message to the screens TTS is routed to.
    folder: where audio files go (served at /cache/tts/)."""

    def __init__(self, settings, play, folder, synth=None, voices=None):
        self.S = settings
        self.play = play
        self.folder = Path(folder)
        self.synth = synth or edge_synth
        self.list_voices = voices or edge_voices
        self.waiting = collections.deque()
        self.wake = asyncio.Event()
        self.skip_now = asyncio.Event()
        self.last_said = {}             # person -> time, for the cooldown
        self.speaking = None
        self.voices_cache = (0.0, None)
        self.counts = {"read": 0, "skipped": 0}
        self.last_error = ""

    # ── what gets read ──
    def check(self, text, who, source):
        """Why a message won't be read (or None). Changes nothing."""
        S = self.S
        if not S["tts_enabled"]:
            return "text to speech is off"
        if source == "tiktok" and not S["tts_tiktok_chat"]:
            return "reading TikTok chat is off"
        text = (text or "").strip()
        if not text:
            return "empty"
        if text.startswith("!"):
            return "a command"
        if LINK_RE.search(text):
            return "has a link"
        low = text.lower()
        for w in blocked_words(S["tts_blocked"]):
            if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", low):   # whole words: "ass" isn't in "class"
                return "has a blocked word"
        key = (who or "").lower()
        if key and time.monotonic() - self.last_said.get(key, -1e9) < S["tts_cooldown"]:
            return "cooldown"
        return None

    def say(self, text, who="", source="mixitup", screen=None):
        """Queue a message to be read aloud. Returns (queued, reason)."""
        why = self.check(text, who, source)
        if why:
            self.counts["skipped"] += 1
            return False, why
        text = re.sub(r"\s+", " ", text.strip())
        limit = int(self.S["tts_max_chars"])
        if len(text) > limit:
            text = text[:limit].rsplit(" ", 1)[0] or text[:limit]
        if who:
            self.last_said[who.lower()] = time.monotonic()
            if len(self.last_said) > 2000:
                cutoff = time.monotonic() - 3600
                self.last_said = {k: t for k, t in self.last_said.items() if t > cutoff}
        spoken = fill(self.S["tts_format"], name=who, message=text) if who else text
        while len(self.waiting) >= MAX_WAITING:
            self.waiting.popleft()           # chat is busy: the oldest unread one goes
            self.counts["skipped"] += 1
        self.waiting.append({"spoken": spoken, "text": text, "from": who, "source": source,
                             "screen": screen, "at": time.monotonic()})
        self.wake.set()
        return True, None

    def skip(self):
        """Stop the message being read now (the next one follows)."""
        self.skip_now.set()

    def clear(self):
        self.waiting.clear()
        self.skip_now.set()

    def status(self):
        return {"enabled": bool(self.S["tts_enabled"]), "waiting": len(self.waiting),
                "speaking": self.speaking["text"] if self.speaking else None,
                "counts": dict(self.counts), "error": self.last_error}

    async def voices(self):
        """All voices (cached for a day)."""
        at, cached = self.voices_cache
        if cached is None or time.time() - at > 86400:
            cached = await self.list_voices()
            self.voices_cache = (time.time(), cached)
        return cached

    async def audio(self, text):
        """MP3 for text in the chosen voice; returns (path, seconds)."""
        data = await self.synth(text, self.S["tts_voice"], self.S["tts_rate"])
        self.folder.mkdir(parents=True, exist_ok=True)
        now = time.time()
        for old in self.folder.glob("*.mp3"):
            try:
                if now - old.stat().st_mtime > KEEP_FILES:
                    old.unlink()
            except OSError:
                pass
        name = hashlib.sha1(f"{uuid.uuid4()}".encode()).hexdigest()[:16] + ".mp3"
        path = self.folder / name
        path.write_bytes(data)
        return path, len(data) / BYTES_PER_SECOND

    # ── the reader ──
    async def worker(self):
        while True:
            while not self.waiting:
                self.wake.clear()
                await self.wake.wait()
            item = self.waiting.popleft()
            if time.monotonic() - item["at"] > MAX_AGE:
                self.counts["skipped"] += 1
                continue
            try:
                path, secs = await self.audio(item["spoken"])
                self.last_error = ""
            except Exception as e:
                self.last_error = f"{type(e).__name__}: {e}"[:200]
                log.warning("tts failed: %s", self.last_error)
                await asyncio.sleep(2)
                continue
            self.speaking = item
            self.skip_now.clear()
            msg = {"type": "tts", "src": f"/cache/tts/{path.name}", "seconds": round(secs, 2),
                   "text": item["text"], "from": item["from"], "source": item["source"],
                   "volume": self.S["tts_volume"], "show": self.S["tts_show_text"]}
            try:
                await self.play(msg, item["screen"])
                try:
                    await asyncio.wait_for(self.skip_now.wait(), secs + 0.5)
                except asyncio.TimeoutError:
                    pass
                self.counts["read"] += 1
            finally:
                self.speaking = None
                await self.play({"type": "tts_end"}, item["screen"])
