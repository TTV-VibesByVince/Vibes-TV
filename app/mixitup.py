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


def identifiers(kind, who, **extra):
    """The special identifiers a command gets (MixItUp adds the $)."""
    out = {"tiktokevent": kind, "tiktokuser": who.get("user", ""), "tiktokname": who.get("display", ""),
           "tiktokavatar": who.get("avatar", "")}
    if kind == "sub":
        out["tiktokmonths"] = str(extra.get("months") or 1)
    if kind == "gift":
        out.update(tiktokgift=str(extra.get("gift", "")), tiktokgiftcount=str(extra.get("count", 1)),
                   tiktokcoins=str(extra.get("coins", 0)))
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
        cmd = (self.S["tiktok_commands"] or {}).get(kind)
        if not cmd or not self.base():
            return None
        if kind == "gift" and int(extra.get("coins") or 0) < self.S["tiktok_command_gift_coins"]:
            return None
        task = asyncio.create_task(self.run(cmd, kind, identifiers(kind, who, **extra), who.get("user", "")))
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
