"""TikTok LIVE alerts for Vibe TV (optional, off by default).

Listens to your own TikTok LIVE with TikTokLive (https://github.com/isaackogan/TikTokLive),
an unofficial, open source Python library that reads the same live feed the
TikTok app shows. Follows, subscriptions and gifts become Vibe TV alerts and
go through the same queues and routing as the MixItUp ones.

TikTokLive isn't made or supported by TikTok, so it can break when TikTok
changes things. It's imported only when the feature is switched on, so the
rest of Vibe TV never depends on it.
"""
import asyncio
import logging
import time

log = logging.getLogger("vibetv.tiktok")

RETRY_OFFLINE = 60          # seconds between "are you live yet?" checks
RETRY_ERROR = (15, 300)     # back-off after an error: first, longest
FOLLOW_MEMORY = 3600        # a re-follow within this many seconds isn't shown again


def first_url(image):
    """The first link of a TikTok image (avatar, gift picture), or ''."""
    urls = getattr(image, "url_list", None) or []
    return urls[0] if urls else ""


def person(user):
    """A TikTokLive user as the plain dict Vibe TV's alerts use."""
    handle = (getattr(user, "display_id", "") or getattr(user, "unique_id", "") or "").strip()
    name = (getattr(user, "nickname", "") or "").strip()
    return {"user": handle or name or "someone", "display": name or handle or "someone",
            "avatar": first_url(getattr(user, "avatar_thumb", None))}


class TikTokWatcher:
    """Keeps one connection to the streamer's TikTok LIVE while it's switched on.

    settings: the Settings object (reads tiktok_* keys).
    alert(ev): queues an alert dict; returns the screens it went to.
    chat(who, text): optional, called with each chat message (text to speech).
    """

    def __init__(self, settings, alert, chat=None):
        self.S = settings
        self.alert = alert
        self.chat_to = chat
        self.task = None
        self.config = None
        self.state, self.detail, self.since = "off", "", time.time()
        self.followed = {}
        self.counts = {"follow": 0, "sub": 0, "gift": 0, "chat": 0}

    # ── what the settings page shows ──
    def set_state(self, state, detail=""):
        if (state, detail) != (self.state, self.detail):
            log.info("tiktok: %s%s", state, f" ({detail})" if detail else "")
        self.state, self.detail, self.since = state, detail, time.time()

    def status(self):
        return {"state": self.state, "detail": self.detail, "username": self.S["tiktok_username"],
                "since": int(self.since), "counts": dict(self.counts)}

    # ── start / stop when the settings change ──
    def reconfigure(self):
        cfg = (bool(self.S["tiktok_enabled"]), self.S["tiktok_username"].lower(), self.S["tiktok_sign_key"])
        running = self.task is not None and not self.task.done()
        if cfg == self.config and (running or not cfg[0]):
            return
        self.config = cfg
        if running:
            self.task.cancel()
        self.task = None
        enabled, username, key = cfg
        if not enabled:
            self.set_state("off")
        elif not username:
            self.set_state("error", "Enter your TikTok username")
        else:
            self.task = asyncio.create_task(self.run(username, key))

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except BaseException:
                pass
        self.task = None

    # ── the connection loop ──
    async def run(self, username, key):
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.client.errors import UserOfflineError
            from TikTokLive.client.web.web_settings import WebDefaults
            from TikTokLive.events import CommentEvent, FollowEvent, GiftEvent, SubNotifyEvent
        except ImportError:
            self.set_state("error", "The TikTokLive library isn't installed in this image")
            return
        # an optional key for the signing service TikTokLive uses (eulerstream.com)
        WebDefaults.tiktok_sign_api_key = key or None
        wait = RETRY_ERROR[0]
        while True:
            client = TikTokLiveClient(unique_id=username)

            @client.on(FollowEvent)
            async def _follow(e):
                self.follow(person(e.user))

            @client.on(CommentEvent)
            async def _chat(e):
                self.chat(person(e.user), getattr(e, "comment", "") or getattr(e, "content", "") or "")

            @client.on(SubNotifyEvent)
            async def _sub(e):
                self.subscribe(person(e.user), getattr(e, "sub_month", 0) or 0)

            @client.on(GiftEvent)
            async def _gift(e):
                g = e.gift
                streakable = bool(g and getattr(g, "type", 0) == 1)
                self.gift(person(e.user), getattr(g, "name", "") or "Gift", first_url(getattr(g, "image", None)),
                          getattr(g, "diamond_count", 0) or 0, getattr(e, "repeat_count", 1) or 1,
                          streaking=streakable and not getattr(e, "repeat_end", 0))

            try:
                self.set_state("connecting", "@" + username)
                loop = await client.start(fetch_live_check=True)
                self.set_state("live", "@" + username)
                wait = RETRY_ERROR[0]
                await loop
                self.set_state("waiting", "Stream ended. Checking again every minute")
                await asyncio.sleep(RETRY_OFFLINE)
            except asyncio.CancelledError:
                raise
            except UserOfflineError:
                self.set_state("waiting", f"@{username} isn't live. Checking every minute")
                await asyncio.sleep(RETRY_OFFLINE)
            except Exception as e:
                self.set_state("error", f"{type(e).__name__}: {e}"[:200] + f" · retrying in {wait}s")
                await asyncio.sleep(wait)
                wait = min(wait * 2, RETRY_ERROR[1])
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

    # ── events, as plain values (the tests call these directly) ──
    def follow(self, who):
        now = time.monotonic()
        key = who["user"].lower()
        if now - self.followed.get(key, -FOLLOW_MEMORY) < FOLLOW_MEMORY:
            return None                     # follow / unfollow / follow spam
        self.followed = {k: t for k, t in self.followed.items() if now - t < FOLLOW_MEMORY}
        self.followed[key] = now
        self.counts["follow"] += 1
        return self.alert({"type": "follow", "platform": "tiktok", **who, "clip": False})

    def chat(self, who, text):
        self.counts["chat"] += 1
        if self.chat_to and text.strip():
            return self.chat_to(who, text)
        return None

    def subscribe(self, who, months=0):
        self.counts["sub"] += 1
        kind = "resub" if months and months > 1 else "sub"
        return self.alert({"type": kind, "platform": "tiktok", **who, "clip": False,
                           "tier": None, "months": months if kind == "resub" else None, "message": ""})

    def gift(self, who, name, image, coins_each, count=1, streaking=False):
        """A combo (tapping the same gift again and again) arrives as one
        event per tap while streaking; only the last one is shown, with the total."""
        if streaking:
            return None
        coins = max(0, int(coins_each)) * max(1, int(count))
        if coins < self.S["tiktok_min_coins"]:
            return None
        self.counts["gift"] += 1
        return self.alert({"type": "tiktok_gift", "platform": "tiktok", **who, "clip": False,
                           "gift": {"name": str(name)[:40], "image": image}, "count": max(1, int(count)),
                           "coins": coins})
