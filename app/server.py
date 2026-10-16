"""Vibe TV - plays a looping logo on a TV and shows shoutout / raid cards and
Twitch clips when MixItUp sends web requests.

MixItUp URLs (unchanged since 1.0):
  /shoutout/<user>   ?avatar= &display= &game= &clip=0|1 &sound=0|1
  /raid/<user>       same, plus &viewers=N
  /message?text=...  &from=
  /logo              clear the queue and go back to the logo
  /reload            reload every TV page
  /status            JSON status
Added in 1.2:
  /follow/<user>             ?avatar= &display=      "Thanks for the follow"
  /gift/<gifter>?to=<user>   one gifted sub; gifts from the same person that
                             arrive close together are shown as one screen
  /giftbomb/<gifter>?count=N a mass gift (recipients from /gift calls join it)
TV page: /  or  /tv  (?mode=lite or ?mode=full to override)   Settings: /admin
"""

import asyncio
import base64
import hmac
import io
import json
import logging
import os
import random
import re
import time
from pathlib import Path

import aiohttp
from aiohttp import web
from PIL import Image

VERSION = "1.2"

BASE = Path(__file__).parent
STATIC = BASE / "static"
MEDIA = Path(os.getenv("MEDIA_DIR", "/media"))
CACHE = Path(os.getenv("CACHE_DIR", "/cache"))
CONFIG = Path(os.getenv("CONFIG_DIR", "/config"))
PORT = int(os.getenv("PORT", "8777"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,25}$")
HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")
VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_UPLOAD = 1024 * 1024 * 1024  # 1 GB

log = logging.getLogger("vibe-tv")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _env_num(name, default):
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return float(default)


# ── Settings ─────────────────────────────────────────────────────────────
# Environment variables give the starting values (so an existing compose file
# keeps working); anything saved on the /admin page wins after that.

SCHEMA = {
    # key: (type, default)
    "logo":                 (str,   ""),          # file in media/, "" = logo.mp4/.webm/.mov
    "logo_fit":             (str,   "cover"),     # cover | contain
    "card_seconds":         (float, _env_num("CARD_SECONDS", 8)),
    "raid_seconds":         (float, _env_num("RAID_SECONDS", 12)),
    "message_seconds":      (float, _env_num("MESSAGE_SECONDS", 10)),
    "follow_seconds":       (float, _env_num("FOLLOW_SECONDS", 6)),
    "gift_seconds":         (float, _env_num("GIFT_SECONDS", 10)),
    "tv_mode":              (str,   os.getenv("TV_MODE", "auto")),   # auto | full | lite
    "max_clip_seconds":     (float, _env_num("MAX_CLIP_SECONDS", 30)),
    "clips":                (bool,  os.getenv("CLIPS", "1") == "1"),
    "clip_sound":           (bool,  os.getenv("CLIP_SOUND", "0") == "1"),
    "twitch_client_id":     (str,   os.getenv("TWITCH_CLIENT_ID", "")),
    "twitch_client_secret": (str,   os.getenv("TWITCH_CLIENT_SECRET", "")),
    "govee_color_url":      (str,   os.getenv("GOVEE_COLOR_URL", "")),
    "govee_raid_url":       (str,   os.getenv("GOVEE_RAID_URL", "")),
    "govee_reset_url":      (str,   os.getenv("GOVEE_RESET_URL", "")),
}
SECRET_KEYS = {"twitch_client_secret"}
LIMITS = {"card_seconds": (2, 60), "raid_seconds": (4, 60),
          "message_seconds": (2, 60), "max_clip_seconds": (5, 60),
          "follow_seconds": (2, 60), "gift_seconds": (4, 60)}
GIFT_WINDOW = 3.0       # seconds of quiet before a batch of gifts is shown
GIFT_MAX_WAIT = 12.0    # never hold a batch longer than this
MAX_QUEUE = 25          # follows are dropped beyond this (follow-bot floods)


class Settings:
    def __init__(self, path):
        self.path = path
        self.data = {k: d for k, (_, d) in SCHEMA.items()}
        try:
            saved = json.loads(path.read_text("utf-8"))
            self.data.update({k: v for k, v in saved.items() if k in SCHEMA})
        except FileNotFoundError:
            pass
        except Exception as e:
            log.warning("settings file unreadable, using defaults: %s", e)

    def __getitem__(self, key):
        return self.data[key]

    def public(self):
        out = {k: v for k, v in self.data.items() if k not in SECRET_KEYS}
        out["twitch_client_secret_set"] = bool(self.data["twitch_client_secret"])
        return out

    def update(self, changes):
        """Validate and apply; returns a list of problems (empty = saved)."""
        clean, errors = {}, []
        for key, val in changes.items():
            if key not in SCHEMA:
                continue
            kind = SCHEMA[key][0]
            if key in SECRET_KEYS and val in (None, ""):
                continue                        # blank = keep the saved secret
            try:
                if kind is bool:
                    val = val if isinstance(val, bool) else str(val).lower() in ("1", "true", "yes", "on")
                elif kind is float:
                    val = float(val)
                    lo, hi = LIMITS.get(key, (0, 3600))
                    if not lo <= val <= hi:
                        raise ValueError(f"must be between {lo} and {hi}")
                else:
                    val = str(val).strip()
            except (TypeError, ValueError) as e:
                errors.append(f"{key}: {e}")
                continue
            if key == "logo_fit" and val not in ("cover", "contain"):
                errors.append("logo_fit: cover or contain")
                continue
            if key == "tv_mode" and val not in ("auto", "full", "lite"):
                errors.append("tv_mode: auto, full or lite")
                continue
            if key == "logo" and val and not media_path(val):
                errors.append("logo: no such file in the media folder")
                continue
            if key.startswith("govee_") and val and not val.startswith(("http://", "https://")):
                errors.append(f"{key}: must start with http://")
                continue
            if key == "twitch_client_secret" and val == "-":
                val = ""                        # "-" clears it
            clean[key] = val
        if errors:
            return errors
        self.data.update(clean)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), "utf-8")
        os.replace(tmp, self.path)
        return []


S = Settings(CONFIG / "settings.json")


def media_path(name):
    """A file directly inside the media folder, or None. Blocks ../ tricks."""
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    p = MEDIA / name
    if p.suffix.lower() not in VIDEO_EXT | IMAGE_EXT or not p.is_file():
        return None
    return p


def logo_info():
    name = S["logo"] if media_path(S["logo"]) else ""
    if not name:
        for cand in ("logo.mp4", "logo.webm", "logo.mov"):
            if (MEDIA / cand).exists():
                name = cand
                break
    common = {"logo_fit": S["logo_fit"], "tv_mode": S["tv_mode"]}
    if not name:
        return {"logo": "", "logo_kind": "", **common}
    kind = "image" if Path(name).suffix.lower() in IMAGE_EXT else "video"
    return {"logo": f"/media/{name}", "logo_kind": kind, **common}


def logo_url():
    return logo_info()["logo"]


# ── Twitch ───────────────────────────────────────────────────────────────

class Twitch:
    def __init__(self, session):
        self.session = session
        self.token = None
        self.token_expires = 0
        self.token_for = None

    @property
    def enabled(self):
        return bool(S["twitch_client_id"] and S["twitch_client_secret"])

    async def _token(self):
        creds = (S["twitch_client_id"], S["twitch_client_secret"])
        if self.token and self.token_for == creds and time.time() < self.token_expires - 60:
            return self.token
        async with self.session.post(
            "https://id.twitch.tv/oauth2/token",
            params={"client_id": creds[0], "client_secret": creds[1],
                    "grant_type": "client_credentials"},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            r.raise_for_status()
            data = await r.json()
        self.token, self.token_for = data["access_token"], creds
        self.token_expires = time.time() + data.get("expires_in", 3600)
        return self.token

    async def _get(self, path, params):
        token = await self._token()
        headers = {"Client-Id": S["twitch_client_id"], "Authorization": f"Bearer {token}"}
        async with self.session.get(f"https://api.twitch.tv/helix/{path}", params=params,
                                    headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 401:
                self.token = None
            r.raise_for_status()
            return (await r.json()).get("data", [])

    async def user(self, login):
        users = await self._get("users", {"login": login})
        if not users:
            return None
        u = users[0]
        info = {"id": u["id"], "login": u["login"], "display_name": u["display_name"],
                "avatar": u["profile_image_url"], "game": ""}
        channels = await self._get("channels", {"broadcaster_id": u["id"]})
        if channels:
            info["game"] = channels[0].get("game_name", "")
        return info

    async def users(self, logins):
        """{login: {display_name, avatar}} for up to 100 logins in one call."""
        out = {}
        for i in range(0, len(logins), 100):
            batch = [("login", l) for l in logins[i:i + 100]]
            for u in await self._get("users", batch):
                out[u["login"]] = {"display_name": u["display_name"], "avatar": u["profile_image_url"]}
        return out

    async def pick_clip(self, broadcaster_id):
        clips = await self._get("clips", {"broadcaster_id": broadcaster_id, "first": 20})
        limit = S["max_clip_seconds"]
        clips = [c for c in clips if c.get("duration", 0) <= limit] or clips
        if not clips:
            return None
        top = sorted(clips, key=lambda c: c.get("view_count", 0), reverse=True)[:8]
        return random.choice(top)


def download_clip(clip_id, url):
    import yt_dlp

    out = CACHE / f"{clip_id}.mp4"
    if out.exists() and out.stat().st_size > 0:
        out.touch()
        return out
    opts = {"outtmpl": str(out), "format": "best[ext=mp4]/best", "quiet": True,
            "noprogress": True, "overwrites": True, "socket_timeout": 15}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return out if out.exists() else None


def prune_cache(keep=40):
    files = sorted(CACHE.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        try:
            f.unlink()
        except OSError:
            pass


def dominant_hex(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((64, 64))
    pal = img.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    palette = pal.getpalette()
    best, best_score = (145, 70, 255), -1
    for count, idx in pal.getcolors():
        r, g, b = palette[idx * 3: idx * 3 + 3]
        mx, mn = max(r, g, b), min(r, g, b)
        sat = (mx - mn) / mx if mx else 0
        bright = mx / 255
        if bright < 0.15:
            continue
        score = count * (0.25 + sat) * (0.5 + bright)
        if score > best_score:
            best, best_score = (r, g, b), score
    return "{:02x}{:02x}{:02x}".format(*best)


# ── The show ─────────────────────────────────────────────────────────────

class TV:
    def __init__(self):
        self.clients = {}          # ws -> {"preview": bool}
        self.queue = asyncio.Queue()
        self.current = None
        self.session = None
        self.twitch = None
        self.running = None
        self.last_govee = ""
        self.gifts = {}            # gifter login -> batch being collected

    @property
    def tv_count(self):
        return sum(1 for c in self.clients.values() if not c["preview"])

    async def broadcast(self, payload):
        msg = json.dumps(payload)
        for ws in list(self.clients):
            try:
                await ws.send_str(msg)
            except Exception:
                self.clients.pop(ws, None)

    async def call_url(self, template, hex_color=""):
        if not template:
            return "not set"
        url = template.replace("{hex}", hex_color or "")
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as r:
                body = (await r.text())[:120]
                result = f"{r.status} {body}".strip()
        except Exception as e:
            result = f"failed: {e.__class__.__name__} {e}".strip()
            log.warning("light call %s failed: %s", url, e)
        self.last_govee = result
        return result

    async def govee(self, hex_color, raid=False):
        if not hex_color:
            await self.call_url(S["govee_reset_url"])
        elif raid and S["govee_raid_url"]:
            await self.call_url(S["govee_raid_url"], hex_color)
        else:
            await self.call_url(S["govee_color_url"], hex_color)

    async def avatar_color(self, url):
        if not url:
            return None
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                r.raise_for_status()
                data = await r.content.read(5 * 1024 * 1024)
            return await asyncio.get_running_loop().run_in_executor(None, dominant_hex, data)
        except Exception as e:
            log.warning("avatar color failed: %s", e)
            return None

    async def build_profile(self, ev):
        login = ev["user"]
        info = {"login": login.lower(), "display_name": ev.get("display") or login,
                "avatar": ev.get("avatar") or "", "game": ev.get("game") or "", "id": None}
        if self.twitch.enabled:
            try:
                api = await self.twitch.user(login.lower())
                if api:
                    info.update({k: v for k, v in api.items() if v})
                    if ev.get("avatar"):
                        info["avatar"] = ev["avatar"]
                    if ev.get("display"):
                        info["display_name"] = ev["display"]
            except Exception as e:
                log.warning("twitch lookup failed for %s: %s", login, e)
        return info

    async def recipient_profiles(self, logins):
        people = [{"login": l.lower(), "display_name": l, "avatar": ""} for l in logins]
        if people and self.twitch.enabled:
            try:
                found = await self.twitch.users([p["login"] for p in people])
                for p in people:
                    p.update(found.get(p["login"], {}))
            except Exception as e:
                log.warning("twitch lookup failed for gift recipients: %s", e)
        return people

    # ── gifted subs arrive one request per recipient; batch them ──
    async def add_gift(self, gifter, recipient=None, count=None, avatar=None, display=None):
        key = gifter.lower()
        now = time.monotonic()
        b = self.gifts.get(key)
        if b is None:
            b = self.gifts[key] = {"user": gifter, "recipients": [], "count": None,
                                   "avatar": None, "display": None, "first": now, "task": None}
        if recipient and recipient.lower() not in {r.lower() for r in b["recipients"]}:
            b["recipients"].append(recipient)
        if count:
            b["count"] = max(b["count"] or 0, count)
        b["avatar"] = avatar or b["avatar"]
        b["display"] = display or b["display"]
        if b["task"]:
            b["task"].cancel()
        complete = b["count"] and len(b["recipients"]) >= b["count"]
        wait = 0.3 if complete else min(GIFT_WINDOW, max(GIFT_MAX_WAIT - (now - b["first"]), 0))
        b["task"] = asyncio.create_task(self._flush_gift(key, wait))
        return len(b["recipients"])

    async def _flush_gift(self, key, wait):
        await asyncio.sleep(wait)
        b = self.gifts.pop(key, None)
        if b:
            await self.queue.put({"type": "gift", "user": b["user"], "avatar": b["avatar"],
                                  "display": b["display"], "recipients": b["recipients"],
                                  "count": b["count"] or len(b["recipients"]), "clip": False})

    async def fetch_clip(self, broadcaster_id):
        if not (self.twitch.enabled and broadcaster_id):
            return None
        try:
            clip = await self.twitch.pick_clip(broadcaster_id)
            if not clip:
                return None
            path = await asyncio.get_running_loop().run_in_executor(None, download_clip, clip["id"], clip["url"])
            prune_cache()
            if not path:
                return None
            return {"src": f"/cache/{path.name}", "title": clip.get("title", ""),
                    "duration": min(float(clip.get("duration", 20)), S["max_clip_seconds"])}
        except Exception as e:
            log.warning("clip fetch failed: %s", e)
            return None

    async def run_event(self, ev):
        kind = ev["type"]
        if kind in ("shoutout", "raid"):
            profile = await self.build_profile(ev)
            color = await self.avatar_color(profile["avatar"])
            # The clip downloads while the card is on screen instead of
            # holding the card back.
            want_clip = ev["clip"] if ev.get("clip") is not None else S["clips"]
            can_clip = want_clip and self.twitch.enabled and profile.get("id")
            clip_task = asyncio.create_task(self.fetch_clip(profile["id"])) if can_clip else None
            card_time = S["raid_seconds"] if kind == "raid" else S["card_seconds"]
            sound = ev["sound"] if ev.get("sound") is not None else S["clip_sound"]
            payload = {"type": kind, "user": profile, "color": color, "viewers": ev.get("viewers"),
                       "sound": sound, "card_seconds": card_time, "clip_pending": bool(clip_task)}
            self.current = payload
            await self.broadcast(payload)
            if color:
                asyncio.create_task(self.govee(color, raid=kind == "raid"))
            preload = None
            if clip_task:
                # As soon as the clip is on disk, let the TVs start buffering
                # it, so it is ready the moment the card ends.
                async def announce():
                    c = await asyncio.shield(clip_task)
                    if c:
                        await self.broadcast({"type": "clip_preload", "src": c["src"]})
                preload = asyncio.create_task(announce())
            try:
                await asyncio.sleep(card_time)
                clip = None
                if clip_task:
                    try:     # a little grace if the download is nearly done
                        clip = await asyncio.wait_for(asyncio.shield(clip_task), 0.1 if clip_task.done() else 4)
                    except asyncio.TimeoutError:
                        log.info("clip not ready in time, skipping it")
                if clip:
                    self.current = {"type": "clip", "clip": clip, "user": profile, "color": color, "sound": sound}
                    await self.broadcast(self.current)
                    await asyncio.sleep(clip["duration"] + 1.5)
            finally:
                if preload:
                    preload.cancel()
        elif kind in ("follow", "gift"):
            profile = await self.build_profile(ev)
            color = await self.avatar_color(profile["avatar"])
            payload = {"type": kind, "user": profile, "color": color}
            if kind == "follow":
                secs = S["follow_seconds"]
            else:
                recipients = await self.recipient_profiles(ev.get("recipients", []))
                count = max(ev.get("count") or 0, len(recipients))
                # big gift bombs get a little longer so the names can be read
                secs = S["gift_seconds"] + min(max(len(recipients) - 8, 0) * 0.25, 8)
                payload.update({"recipients": recipients, "count": count})
            payload["card_seconds"] = secs
            self.current = payload
            await self.broadcast(payload)
            if color:
                asyncio.create_task(self.govee(color))
            await asyncio.sleep(secs + 0.6)
        elif kind == "message":
            secs = S["message_seconds"]
            payload = {"type": "message", "text": ev["text"][:140], "from": ev.get("from", ""), "seconds": secs}
            self.current = payload
            await self.broadcast(payload)
            await asyncio.sleep(secs + 1)
        self.current = None
        await self.broadcast({"type": "logo"})
        await self.govee(None)

    async def worker(self):
        while True:
            ev = await self.queue.get()
            try:
                self.running = asyncio.create_task(self.run_event(ev))
                await self.running
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise
                self.current = None
            except Exception as e:
                log.exception("event failed: %s", e)
                self.current = None
                await self.broadcast({"type": "logo"})
            finally:
                self.running = None
                self.queue.task_done()


tv = TV()


# ── helpers ──────────────────────────────────────────────────────────────

def clean_user(raw):
    """Keeps the capitals as typed, so the card reads 'CoolStreamer' even
    without Twitch API keys."""
    user = (raw or "").strip().lstrip("@")
    if not USERNAME_RE.match(user):
        raise web.HTTPBadRequest(text="bad username")
    return user


def flag(request, name, default=None):
    val = request.query.get(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def queued():
    return web.json_response({"ok": True, "queued": tv.queue.qsize()})


# ── MixItUp endpoints (behaviour unchanged) ──────────────────────────────

async def index(request):
    return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    preview = request.query.get("preview") == "1"
    tv.clients[ws] = {"preview": preview}
    log.info("%s connected (%d tvs)", "preview" if preview else "tv", tv.tv_count)
    await ws.send_str(json.dumps({"type": "hello", "version": VERSION, **logo_info()}))
    try:
        async for _ in ws:
            pass
    finally:
        tv.clients.pop(ws, None)
        log.info("%s disconnected (%d tvs)", "preview" if preview else "tv", tv.tv_count)
    return ws


def _card_event(request, kind):
    ev = {"type": kind, "user": clean_user(request.match_info["user"]),
          "avatar": request.query.get("avatar"), "display": request.query.get("display"),
          "game": request.query.get("game"), "clip": flag(request, "clip"),
          "sound": flag(request, "sound")}
    if kind == "raid":
        viewers = request.query.get("viewers", "").strip()
        ev["viewers"] = int(viewers) if viewers.isdigit() else None
    return ev


async def shoutout(request):
    await tv.queue.put(_card_event(request, "shoutout"))
    return queued()


async def raid(request):
    await tv.queue.put(_card_event(request, "raid"))
    return queued()


async def follow(request):
    if tv.queue.qsize() >= MAX_QUEUE:
        return web.json_response({"ok": False, "skipped": "queue full"})
    ev = _card_event(request, "follow")
    ev["clip"] = False
    await tv.queue.put(ev)
    return queued()


def _count(request):
    raw = (request.query.get("count") or "").strip()
    return min(int(raw), 1000) if raw.isdigit() else None


async def gift(request):
    """One gifted sub: /gift/<gifter>?to=<recipient>. Several from the same
    gifter within a few seconds become one screen."""
    gifter = clean_user(request.match_info["user"])
    to = request.query.get("to") or request.query.get("recipient") or ""
    recipients = [clean_user(r) for r in to.replace(";", ",").split(",") if r.strip()]
    n = 0
    for r in recipients or [None]:
        n = await tv.add_gift(gifter, r, _count(request), request.query.get("avatar"),
                              request.query.get("display"))
    return web.json_response({"ok": True, "collected": n})


async def giftbomb(request):
    """A mass gift: /giftbomb/<gifter>?count=N. Recipients sent with /gift
    in the next few seconds are shown with it."""
    gifter = clean_user(request.match_info["user"])
    n = await tv.add_gift(gifter, None, _count(request) or 1, request.query.get("avatar"),
                          request.query.get("display"))
    return web.json_response({"ok": True, "collected": n})


async def message(request):
    text = (request.query.get("text") or "").strip()
    if not text:
        raise web.HTTPBadRequest(text="text required")
    await tv.queue.put({"type": "message", "text": text, "from": request.query.get("from", "")})
    return queued()


async def logo(request):
    for b in tv.gifts.values():
        if b["task"]:
            b["task"].cancel()
    tv.gifts.clear()
    while not tv.queue.empty():
        tv.queue.get_nowait()
        tv.queue.task_done()
    if tv.running and not tv.running.done():
        tv.running.cancel()
    tv.current = None
    await tv.broadcast({"type": "logo"})
    await tv.govee(None)
    return web.json_response({"ok": True})


async def reload(request):
    await tv.broadcast({"type": "reload"})
    return web.json_response({"ok": True})


async def status(request):
    return web.json_response({
        "version": VERSION,
        "tvs_connected": tv.tv_count,
        "queued": tv.queue.qsize(),
        "showing": tv.current["type"] if tv.current else "logo",
        "twitch_api": tv.twitch.enabled,
        "logo": logo_url() or "missing - upload one at /admin or put logo.mp4 in the media folder",
    })


# ── Admin page + API ─────────────────────────────────────────────────────

@web.middleware
async def admin_auth(request, handler):
    if ADMIN_PASSWORD and (request.path == "/admin" or request.path.startswith("/api/")):
        ok = False
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                _, _, pw = base64.b64decode(header[6:]).decode().partition(":")
                ok = hmac.compare_digest(pw.encode(), ADMIN_PASSWORD.encode())
            except Exception:
                ok = False
        if not ok:
            raise web.HTTPUnauthorized(headers={"WWW-Authenticate": 'Basic realm="Vibe TV"'})
    return await handler(request)


async def admin_page(request):
    return web.FileResponse(STATIC / "admin.html", headers={"Cache-Control": "no-cache"})


def list_media():
    out = []
    active = logo_url().rsplit("/", 1)[-1] if logo_url() else ""
    for p in sorted(MEDIA.iterdir(), key=lambda p: p.name.lower()):
        ext = p.suffix.lower()
        if p.is_file() and ext in VIDEO_EXT | IMAGE_EXT and not p.name.startswith("."):
            st = p.stat()
            out.append({"name": p.name, "url": f"/media/{p.name}",
                        "kind": "image" if ext in IMAGE_EXT else "video",
                        "size": st.st_size, "modified": int(st.st_mtime),
                        "active": p.name == active})
    return out


async def api_state(request):
    return web.json_response({
        "version": VERSION,
        "settings": S.public(),
        "status": {"tvs_connected": tv.tv_count, "queued": tv.queue.qsize(),
                   "showing": tv.current["type"] if tv.current else "logo",
                   "twitch_api": tv.twitch.enabled, "last_lights": tv.last_govee,
                   **logo_info()},
        "media": list_media(),
        "password_protected": bool(ADMIN_PASSWORD),
    })


async def api_settings(request):
    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text="JSON body required")
    before = logo_info()
    errors = S.update(body if isinstance(body, dict) else {})
    if errors:
        return web.json_response({"ok": False, "errors": errors}, status=400)
    after = logo_info()
    if after != before:
        await tv.broadcast({"type": "logo_src", **after})
    return web.json_response({"ok": True, "settings": S.public()})


def safe_upload_name(raw):
    name = Path(raw or "").name
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"[^A-Za-z0-9 _.-]", "", stem).strip(" .")[:80] or "logo"
    return stem + ext.lower()


async def api_upload(request):
    reader = await request.multipart()
    field = await reader.next()
    while field is not None and field.name != "file":
        field = await reader.next()
    if field is None or not field.filename:
        raise web.HTTPBadRequest(text="no file")
    name = safe_upload_name(field.filename)
    if Path(name).suffix not in VIDEO_EXT | IMAGE_EXT:
        raise web.HTTPBadRequest(text="Use a video (mp4, webm, mov) or an image (png, jpg, gif, webp)")
    dest = MEDIA / name
    n = 2
    while dest.exists():
        dest = MEDIA / f"{Path(name).stem}-{n}{Path(name).suffix}"
        n += 1
    tmp = MEDIA / f".upload-{os.getpid()}-{time.time_ns()}"
    size = 0
    try:
        with open(tmp, "wb") as f:
            while chunk := await field.read_chunk(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise web.HTTPRequestEntityTooLarge(max_size=MAX_UPLOAD, actual_size=size)
                f.write(chunk)
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    log.info("uploaded %s (%d bytes)", dest.name, size)
    return web.json_response({"ok": True, "name": dest.name, "media": list_media()})


async def api_delete_media(request):
    p = media_path(request.match_info["name"])
    if not p:
        raise web.HTTPNotFound(text="no such file")
    before = logo_info()
    p.unlink()
    if S["logo"] == p.name:
        S.update({"logo": ""})
    after = logo_info()
    if after != before:
        await tv.broadcast({"type": "logo_src", **after})
    return web.json_response({"ok": True, "media": list_media()})


async def api_test_lights(request):
    which = request.query.get("which", "color")
    hex_color = request.query.get("hex", "9146ff")
    if not HEX_RE.match(hex_color):
        raise web.HTTPBadRequest(text="hex must be 6 digits")
    template = {"color": S["govee_color_url"], "raid": S["govee_raid_url"],
                "reset": S["govee_reset_url"]}.get(which, "")
    result = await tv.call_url(template, hex_color.lower())
    return web.json_response({"ok": not result.startswith(("failed", "not set")), "result": result})


async def api_test_twitch(request):
    if not tv.twitch.enabled:
        return web.json_response({"ok": False, "result": "Client ID and secret not set"})
    tv.twitch.token = None
    try:
        user = await tv.twitch.user(clean_user(request.query.get("user", "twitch")).lower())
        text = f"Connected. Found {user['display_name']}" if user else "Connected (user not found)"
        return web.json_response({"ok": True, "result": text})
    except Exception as e:
        return web.json_response({"ok": False, "result": f"{e.__class__.__name__}: {e}"})


# ── app ──────────────────────────────────────────────────────────────────

async def on_startup(app):
    tv.session = aiohttp.ClientSession()
    tv.twitch = Twitch(tv.session)
    app["worker"] = asyncio.create_task(tv.worker())
    log.info("Vibe TV v%s on :%d (twitch api: %s, logo: %s, admin password: %s)",
             VERSION, PORT, tv.twitch.enabled, logo_url() or "none", "on" if ADMIN_PASSWORD else "off")


async def on_cleanup(app):
    app["worker"].cancel()
    await tv.session.close()


def make_app():
    for d in (MEDIA, CACHE, CONFIG):
        d.mkdir(parents=True, exist_ok=True)
    app = web.Application(middlewares=[admin_auth], client_max_size=4 * 1024 * 1024)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_get("/", index)
    app.router.add_get("/tv", index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_route("*", "/shoutout/{user}", shoutout)
    app.router.add_route("*", "/raid/{user}", raid)
    app.router.add_route("*", "/follow/{user}", follow)
    app.router.add_route("*", "/gift/{user}", gift)
    app.router.add_route("*", "/giftbomb/{user}", giftbomb)
    app.router.add_route("*", "/message", message)
    app.router.add_route("*", "/logo", logo)
    app.router.add_route("*", "/reload", reload)
    app.router.add_get("/status", status)
    app.router.add_get("/admin", admin_page)
    app.router.add_get("/api/state", api_state)
    app.router.add_post("/api/settings", api_settings)
    app.router.add_post("/api/media", api_upload)
    app.router.add_delete("/api/media/{name}", api_delete_media)
    app.router.add_post("/api/test/lights", api_test_lights)
    app.router.add_post("/api/test/twitch", api_test_twitch)
    app.router.add_static("/media", MEDIA, show_index=False)
    app.router.add_static("/cache", CACHE, show_index=False)
    app.router.add_static("/static", STATIC, show_index=False)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=PORT, access_log=None)
