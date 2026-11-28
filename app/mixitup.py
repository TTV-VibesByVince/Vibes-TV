"""Runs MixItUp commands when something happens on TikTok LIVE.

MixItUp has a Developer API (Services > Developer API > Connect) that lets
other programs list its commands and run them:

    GET  {base}/api/v2/commands?skip=0&pageSize=200
    POST {base}/api/v2/commands/{id}   {"Arguments": "...", "SpecialIdentifiers": {...}}

MixItUp only listens on the PC it runs on (localhost:8911), so the NAS
reaches it through a port forward on that PC (see docs/tiktok-mixitup.md).
mixitup_url is that address, for example http://<PC address>:8912.

The command gets the event's details as special identifiers, which MixItUp
commands use with a $ in front: $tiktokuser, $tiktokname, $tiktokgift, ...

TikTok chat commands work the same way: a message starting with one of the
tiktok_chat_commands words (!blue) runs that row's command, with the rest of
the message as its arguments.
"""
import asyncio
import logging
import re
import time

log = logging.getLogger("vibetv.mixitup")

KINDS = ("follow", "sub", "gift", "share")       # TikTok events that can run a command
ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
URL_RE = re.compile(r"^https?://[A-Za-z0-9.\-]+(:\d{1,5})?/?$")
TIMEOUT = 5          # seconds MixItUp gets to answer
LIST_CACHE = 30      # seconds the command list is kept
TRIGGER_RE = re.compile(r"^[a-z0-9_]{1,30}$")
MAX_CHAT_COMMANDS = 50
PERSON_COOLDOWN = 3  # seconds before the same person can run another chat command


def check_chat_commands(val):
    """The tiktok_chat_commands setting: [{"trigger", "id", "cooldown"}]. Returns (clean, error)."""
    if not isinstance(val, list) or len(val) > MAX_CHAT_COMMANDS:
        return None, f"tiktok_chat_commands: a list of up to {MAX_CHAT_COMMANDS}"
    out, seen = [], set()
    for i, row in enumerate(val, 1):
        if not isinstance(row, dict):
            return None, f"tiktok_chat_commands #{i}: bad entry"
        trigger = str(row.get("trigger", "")).strip().lstrip("!").lower()
        cid = str(row.get("id", "")).strip()
        if not trigger and not cid:
            continue                                  # an empty row
        if not TRIGGER_RE.match(trigger):
            return None, f"tiktok_chat_commands #{i}: a word like !blue (letters, numbers and _)"
        if trigger in seen:
            return None, f"tiktok_chat_commands: !{trigger} is there twice"
        if not ID_RE.match(cid):
            return None, f"tiktok_chat_commands !{trigger}: pick a MixItUp command"
        try:
            cooldown = float(row.get("cooldown", 10))
        except (TypeError, ValueError):
            cooldown = -1
        if not 0 <= cooldown <= 3600:
            return None, f"tiktok_chat_commands !{trigger}: cooldown between 0 and 3600 seconds"
        seen.add(trigger)
        out.append({"trigger": trigger, "id": cid, "cooldown": cooldown})
    return out, None


def parse_chat(text):
    """'!Blue now please' -> ('blue', 'now please'); None if it isn't a command."""
    text = (text or "").strip()
    if not text.startswith("!"):
        return None
    word, _, rest = text[1:].partition(" ")
    return word.lower(), rest.strip()


def identifiers(kind, who, **extra):
    """The special identifiers a command gets (MixItUp adds the $)."""
    out = {"tiktokevent": kind, "tiktokuser": who.get("user", ""), "tiktokname": who.get("display", ""),
           "tiktokavatar": who.get("avatar", "")}
    if kind == "sub":
        out["tiktokmonths"] = str(extra.get("months") or 1)
    if kind == "gift":
        out.update(tiktokgift=str(extra.get("gift", "")), tiktokgiftcount=str(extra.get("count", 1)),
                   tiktokcoins=str(extra.get("coins", 0)))
    if kind == "chat":
        out.update(tiktokcommand=str(extra.get("command", "")), tiktokmessage=str(extra.get("message", "")))
    return out


class MixItUp:
    """settings: the Settings object (mixitup_url, tiktok_commands).
    session: a function returning the shared aiohttp ClientSession."""

    def __init__(self, settings, session):
        self.S = settings
        self.session = session
        self.cache = (0.0, None, None)       # (when, url, commands)
        self.last = None                     # the last run: what, when, and how it went
        self.tasks = set()
        self.used = {}                       # chat command -> when it last ran
        self.people = {}                     # person -> when they last ran a chat command

    def base(self):
        url = (self.S["mixitup_url"] or "").strip().rstrip("/")
        return url + "/api/v2" if url else ""

    async def commands(self, fresh=False):
        """MixItUp's commands, by name: [{id, name, type, group, enabled}]. Raises on trouble."""
        base = self.base()
        if not base:
            raise RuntimeError("Enter MixItUp's address first")
        when, url, cached = self.cache
        if not fresh and cached is not None and url == base and time.monotonic() - when < LIST_CACHE:
            return cached
        out, skip = [], 0
        while True:
            async with self.session().get(f"{base}/commands", params={"skip": skip, "pageSize": 200},
                                          timeout=TIMEOUT) as r:
                if r.status != 200:
                    raise RuntimeError(f"MixItUp answered {r.status}")
                data = await r.json(content_type=None)
            page = data.get("Commands") or []
            out += [{"id": c.get("ID", ""), "name": c.get("Name", ""), "type": c.get("Type", ""),
                     "group": c.get("GroupName") or "", "enabled": c.get("IsEnabled", True)} for c in page]
            skip += len(page)
            if not page or skip >= int(data.get("TotalCount") or 0) or skip > 5000:
                break
        out.sort(key=lambda c: (c["type"].lower(), c["name"].lower()))
        self.cache = (time.monotonic(), base, out)
        return out

    def trigger(self, kind, who, **extra):
        """Run the command chosen for this TikTok event, if any (in the background)."""
        if kind == "chat":
            return self.chat(who, extra.get("text", ""))
        cmd = (self.S["tiktok_commands"] or {}).get(kind)
        if not cmd or not self.base():
            return None
        if kind == "gift" and int(extra.get("coins") or 0) < self.S["tiktok_command_gift_coins"]:
            return None
        return self.start(cmd, kind, identifiers(kind, who, **extra), who.get("user", ""))

    def chat(self, who, text, now=None):
        """A TikTok chat message: run its chat command, if it is one and it isn't cooling down."""
        parsed = parse_chat(text)
        if not parsed or not self.base():
            return None
        word, rest = parsed
        row = next((r for r in self.S["tiktok_chat_commands"] or [] if r["trigger"] == word), None)
        if not row:
            return None
        now = time.monotonic() if now is None else now
        person = who.get("user", "").lower()
        if now - self.used.get(word, -1e9) < row["cooldown"] or now - self.people.get(person, -1e9) < PERSON_COOLDOWN:
            return None
        self.used[word] = now
        self.people = {k: t for k, t in self.people.items() if now - t < PERSON_COOLDOWN}
        self.people[person] = now
        ids = identifiers("chat", who, command=word, message=rest)
        return self.start(row["id"], "!" + word, ids, rest)

    def start(self, cmd, kind, ids, args):
        task = asyncio.create_task(self.run(cmd, kind, ids, args))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def run(self, cmd, kind, ids, args=""):
        body = {"Arguments": args, "SpecialIdentifiers": ids}
        try:
            async with self.session().post(f"{self.base()}/commands/{cmd}", json=body, timeout=TIMEOUT) as r:
                ok = r.status == 200
                detail = "" if ok else f"MixItUp answered {r.status}: {(await r.text())[:160]}"
        except asyncio.CancelledError:
            raise
        except Exception as e:
            ok, detail = False, f"Couldn't reach MixItUp ({type(e).__name__})"
        self.last = {"kind": kind, "user": ids.get("tiktokuser", ""), "ok": ok, "detail": detail, "at": int(time.time())}
        if not ok:
            log.warning("mixitup: %s command failed: %s", kind, detail)
        return ok

    def status(self):
        return {"url_set": bool(self.base()), "last": self.last}
