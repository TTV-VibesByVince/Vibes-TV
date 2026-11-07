"""Connect Vibe TV to your Twitch account (optional).

With the app keys alone, Vibe TV can only look up public things (names,
pictures, clips). Connecting your account once (Twitch's device login: a
code you type at twitch.tv/activate) lets it receive your channel's events
live, through Twitch EventSub over a websocket from your server outwards.
Nothing has to be opened to the internet.

Used for the end credits: mods and VIPs who chat, a new list when you go
live, and (optionally) everyone who followed, subbed, gifted, cheered,
raided, shared a watch streak, gigantified an emote, or rode the hype train.

The login is kept in its own file in the config folder, never in the
settings or backups.
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import aiohttp

log = logging.getLogger("vibetv.twitch")

AUTH_URL = "https://id.twitch.tv/oauth2"
HELIX_URL = "https://api.twitch.tv/helix"
EVENTSUB_URL = "wss://eventsub.wss.twitch.tv/ws"
# What Vibe TV asks permission for (shown on Twitch's approval screen)
SCOPES = ["user:read:chat", "moderator:read:followers", "bits:read", "channel:read:hype_train",
          "moderator:read:shoutouts"]
RETRY = (5, 300)              # seconds to wait before reconnecting: first, longest


def subscriptions(user_id):
    """(type, versions to try, condition) for everything Vibe TV listens to."""
    me = {"broadcaster_user_id": user_id}
    chat = {"broadcaster_user_id": user_id, "user_id": user_id}
    return [
        ("stream.online", ["1"], me),
        ("channel.chat.message", ["1"], chat),            # mod / VIP badges
        ("channel.chat.notification", ["1"], chat),       # subs, resubs, gifts, raids, watch streaks
        ("channel.follow", ["2"], {"broadcaster_user_id": user_id, "moderator_user_id": user_id}),
        ("channel.bits.use", ["1"], me),                  # cheers and Power-ups (gigantified emotes)
        ("channel.shoutout.create", ["1"], {"broadcaster_user_id": user_id, "moderator_user_id": user_id}),
        ("channel.hype_train.begin", ["2", "1"], me),
        ("channel.hype_train.progress", ["2", "1"], me),
        ("channel.hype_train.end", ["2", "1"], me),
    ]


def person(login, name=None, avatar=""):
    login = (login or "").strip().lower()
    return {"login": login, "name": (name or login).strip(), "avatar": avatar or ""}


def translate(sub_type, ev):
    """One EventSub notification as a list of (kind, data) for Vibe TV.
    Plain dicts in, plain dicts out: the tests feed this real-shaped payloads."""
    out = []
    text = ((ev.get("message") or {}).get("text") or "").strip()
    if sub_type == "stream.online":
        if ev.get("type", "live") == "live":
            out.append(("online", {}))
    elif sub_type == "channel.chat.message":
        badges = {b.get("set_id") for b in ev.get("badges") or []}
        who = person(ev.get("chatter_user_login"), ev.get("chatter_user_name"))
        if ev.get("source_broadcaster_user_id") and ev.get("source_broadcaster_user_id") != ev.get("broadcaster_user_id"):
            return out                          # shared chat: someone else's chat
        if who["login"] and text:
            you = who["login"] == (ev.get("broadcaster_user_login") or "").lower()
            out.append(("chat", {"user": who, "text": text,
                                 "mod": you or bool(badges & {"broadcaster", "moderator", "lead_moderator"})}))
        if who["login"] and who["login"] != (ev.get("broadcaster_user_login") or "").lower():
            if badges & {"moderator", "lead_moderator"}:     # a lead mod has their own badge instead
                out.append(("seen", {"user": who, "role": "mod"}))
            elif "vip" in badges:
                out.append(("seen", {"user": who, "role": "vip"}))
    elif sub_type == "channel.chat.notification":
        kind = ev.get("notice_type")
        anon = ev.get("chatter_is_anonymous")
        who = person("anonymous", "An anonymous gifter") if anon else \
            person(ev.get("chatter_user_login") or ev.get("chatter_user_name"), ev.get("chatter_user_name"))
        if kind == "sub":
            sub = ev.get("sub") or {}
            out.append(("sub", {"user": who, "tier": "prime" if sub.get("is_prime") else sub.get("sub_tier")}))
        elif kind == "resub":
            resub = ev.get("resub") or {}
            out.append(("resub", {"user": who, "months": resub.get("cumulative_months"), "message": text,
                                  "tier": "prime" if resub.get("is_prime") else resub.get("sub_tier")}))
        elif kind == "sub_gift":
            g = ev.get("sub_gift") or {}
            out.append(("gift", {"user": who, "recipient": person(g.get("recipient_user_login"), g.get("recipient_user_name")),
                                 "count": 1, "tier": g.get("sub_tier")}))
        elif kind == "community_sub_gift":         # a gift bomb: the total first, each recipient as its own sub_gift
            c = ev.get("community_sub_gift") or {}
            out.append(("gift_bomb", {"user": who, "count": c.get("total") or 1, "tier": c.get("sub_tier")}))
        elif kind == "raid":
            r = ev.get("raid") or {}
            out.append(("raid", {"user": person(r.get("user_login"), r.get("user_name"), r.get("profile_image_url")),
                                 "viewers": r.get("viewer_count") or 0}))
        elif kind == "watch_streak":
            w = ev.get("watch_streak") or {}
            out.append(("streak", {"user": who, "count": w.get("streak_count") or 0, "message": text}))
        elif kind == "modiversary":
            out.append(("modiversary", {"user": who, "months": (ev.get("modiversary") or {}).get("months") or 0}))
        # shared_chat_*: another channel's events in a shared chat
    elif sub_type == "channel.follow":
        out.append(("follow", {"user": person(ev.get("user_login"), ev.get("user_name"))}))
    elif sub_type == "channel.bits.use":
        who = person(ev.get("user_login"), ev.get("user_name"))
        if ev.get("type") == "cheer" and ev.get("bits"):
            out.append(("bits", {"user": who, "amount": ev["bits"], "message": text}))
        power = ev.get("power_up") or {}
        if ev.get("type") == "power_up" and power.get("type") == "gigantify_an_emote":
            emote = power.get("emote") or {}
            out.append(("gigantify", {"user": who, "emote_id": emote.get("id"), "emote_name": emote.get("name") or ""}))
    elif sub_type.startswith("channel.hype_train."):
        if ev.get("level"):
            action = {"begin": "start", "progress": "progress", "end": "end"}.get(sub_type.rsplit(".", 1)[1], "progress")
            out.append(("hype", {"level": ev["level"], "action": action,
                                 "progress": ev.get("progress"), "goal": ev.get("goal")}))
    elif sub_type == "channel.shoutout.create":     # you (or a mod) used Twitch's /shoutout
        out.append(("shoutout", {"user": person(ev.get("to_broadcaster_user_login"), ev.get("to_broadcaster_user_name")),
                                 "viewers": ev.get("viewer_count")}))
    return out


class TwitchLive:
    """settings: the Settings object (twitch_client_id / _secret).
    auth_path: where the login is kept. on_event(kind, data): called for each
    event (may return a coroutine)."""

    def __init__(self, settings, auth_path, on_event):
        self.S = settings
        self.path = Path(auth_path)
        self.on_event = on_event
        self.http = None
        self.auth = self.load()
        self.task = None
        self.login_task = None
        self.login = None                 # {"code", "url", "expires"} while waiting for you at twitch.tv/activate
        self.state, self.detail = ("off", "") if not self.auth else ("starting", "")
        self.last_event = None
        self.subscribed = []

    # ── the saved login ──
    def load(self):
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text("utf-8"))
                if data.get("access_token") and data.get("user_id"):
                    return data
        except Exception as e:
            log.warning("twitch login file unreadable: %s", e)
        return None

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.auth), "utf-8")
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def set_state(self, state, detail=""):
        if (state, detail) != (self.state, self.detail):
            log.info("twitch connection: %s%s", state, f" ({detail})" if detail else "")
        self.state, self.detail = state, detail

    def status(self):
        return {"state": self.state, "detail": self.detail,
                "account": self.auth.get("login") if self.auth else None,
                "login": dict(self.login) if self.login else None,
                "events": len(self.subscribed), "last_event": self.last_event}

    def client(self):
        if self.http is None or self.http.closed:
            self.http = aiohttp.ClientSession()
        return self.http

    def creds(self, data):
        data = {"client_id": self.S["twitch_client_id"], **data}
        if self.S["twitch_client_secret"]:
            data["client_secret"] = self.S["twitch_client_secret"]
        return data

    # ── logging in: Twitch's device flow ──
    async def start_login(self):
        if not self.S["twitch_client_id"]:
            raise RuntimeError("Enter your Twitch Client ID (and secret) first, and save")
        async with self.client().post(f"{AUTH_URL}/device", data={"client_id": self.S["twitch_client_id"],
                                                                 "scopes": " ".join(SCOPES)}) as r:
            body = await r.json(content_type=None)
            if r.status != 200:
                raise RuntimeError(body.get("message") or f"Twitch said {r.status}")
        self.login = {"code": body["user_code"], "url": body["verification_uri"],
                      "expires": int(time.time() + body.get("expires_in", 1800))}
        if self.login_task:
            self.login_task.cancel()
        self.login_task = asyncio.create_task(self._wait_for_login(body["device_code"], body.get("interval", 5),
                                                                   body.get("expires_in", 1800)))
        return dict(self.login)

    async def _wait_for_login(self, device_code, interval, expires_in):
        end = time.time() + expires_in
        try:
            while time.time() < end:
                await asyncio.sleep(interval)
                async with self.client().post(f"{AUTH_URL}/token", data=self.creds({
                        "scopes": " ".join(SCOPES), "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})) as r:
                    body = await r.json(content_type=None)
                if r.status == 200 and body.get("access_token"):
                    who = await self.validate(body["access_token"])
                    self.auth = {"access_token": body["access_token"], "refresh_token": body.get("refresh_token"),
                                 "user_id": who["user_id"], "login": who["login"], "scopes": who.get("scopes", []),
                                 "expires": time.time() + body.get("expires_in", 14400)}
                    self.save()
                    self.login = None
                    self.reconfigure(force=True)
                    return
                message = str(body.get("message", ""))
                if "authorization_pending" in message:
                    continue
                if "slow_down" in message:
                    interval += 5
                    continue
                raise RuntimeError(message or f"Twitch said {r.status}")
            raise RuntimeError("The code expired before it was used: press Connect again")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.login = None
            self.set_state("error", f"Couldn't log in: {e}"[:200])

    async def validate(self, token):
        async with self.client().get(f"{AUTH_URL}/validate", headers={"Authorization": f"OAuth {token}"}) as r:
            body = await r.json(content_type=None)
            if r.status != 200:
                raise PermissionError(body.get("message") or "invalid token")
            return body

    async def refresh(self):
        async with self.client().post(f"{AUTH_URL}/token", data=self.creds({
                "grant_type": "refresh_token", "refresh_token": self.auth.get("refresh_token") or ""})) as r:
            body = await r.json(content_type=None)
            if r.status != 200 or not body.get("access_token"):
                raise PermissionError(body.get("message") or "Twitch didn't renew the login")
        self.auth.update({"access_token": body["access_token"], "refresh_token": body.get("refresh_token") or self.auth.get("refresh_token"),
                          "expires": time.time() + body.get("expires_in", 14400)})
        self.save()

    async def token(self):
        """A working access token, renewed when it's close to expiring."""
        if time.time() > self.auth.get("expires", 0) - 300:
            await self.refresh()
        return self.auth["access_token"]

    async def disconnect(self):
        await self.stop()
        if self.login_task:
            self.login_task.cancel()
        self.login, self.auth = None, None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        self.set_state("off")

    # ── staying connected ──
    def reconfigure(self, force=False):
        running = self.task is not None and not self.task.done()
        if running and not force:
            return
        if running:
            self.task.cancel()
        self.task = None
        if self.auth and self.S["twitch_client_id"]:
            self.task = asyncio.create_task(self.run())
        elif not self.login:
            self.set_state("off")

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except BaseException:
                pass
        self.task = None
        if self.http and not self.http.closed:
            await self.http.close()

    async def run(self):
        wait = RETRY[0]
        url = EVENTSUB_URL
        while True:
            try:
                self.set_state("connecting")
                await self.token()
                url = await self.session(url)
                wait = RETRY[0]
                if url:                         # Twitch asked us to move to another server
                    continue
                url = EVENTSUB_URL
            except asyncio.CancelledError:
                raise
            except PermissionError as e:
                self.set_state("error", f"Twitch login no longer works ({e}). Connect again.")
                return
            except Exception as e:
                self.set_state("error", f"{type(e).__name__}: {e}"[:180] + f" · retrying in {wait}s")
                url = EVENTSUB_URL
            await asyncio.sleep(wait)
            wait = min(wait * 2, RETRY[1])

    async def session(self, url):
        """One websocket session. Returns a reconnect URL if Twitch sends one."""
        fresh = url == EVENTSUB_URL
        async with self.client().ws_connect(url, heartbeat=None) as ws:
            timeout = 30
            while True:
                try:
                    msg = await ws.receive(timeout=timeout + 10)
                except asyncio.TimeoutError:
                    raise ConnectionError("Twitch went quiet")
                if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    raise ConnectionError(f"Twitch closed the connection ({ws.close_code})")
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                data = json.loads(msg.data)
                meta, payload = data.get("metadata", {}), data.get("payload", {})
                mtype = meta.get("message_type")
                if mtype == "session_welcome":
                    sess = payload.get("session", {})
                    timeout = sess.get("keepalive_timeout_seconds") or 30
                    if fresh:
                        await self.subscribe(sess["id"])
                    self.set_state("live", "@" + self.auth.get("login", ""))
                elif mtype == "notification":
                    await self.handle(meta.get("subscription_type", ""), payload.get("event") or {})
                elif mtype == "session_reconnect":
                    return payload.get("session", {}).get("reconnect_url")
                elif mtype == "revocation":
                    log.warning("twitch stopped sending %s: %s", meta.get("subscription_type"),
                                payload.get("subscription", {}).get("status"))

    async def subscribe(self, session_id):
        token = await self.token()
        headers = {"Client-Id": self.S["twitch_client_id"], "Authorization": f"Bearer {token}"}
        done, missing = [], []
        for sub_type, versions, condition in subscriptions(self.auth["user_id"]):
            for version in versions:
                body = {"type": sub_type, "version": version, "condition": condition,
                        "transport": {"method": "websocket", "session_id": session_id}}
                async with self.client().post(f"{HELIX_URL}/eventsub/subscriptions", json=body, headers=headers) as r:
                    if r.status in (200, 202):
                        done.append(sub_type)
                        break
                    if r.status == 401:
                        raise PermissionError("Twitch refused the login")
                    reason = (await r.json(content_type=None)).get("message", r.status)
            else:
                missing.append(f"{sub_type} ({reason})")
        self.subscribed = done
        if missing:
            log.warning("twitch: couldn't listen to %s", ", ".join(missing))

    async def handle(self, sub_type, event):
        self.last_event = int(time.time())
        for kind, data in translate(sub_type, event):
            try:
                result = self.on_event(kind, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                log.warning("twitch %s event failed: %s", kind, e)
