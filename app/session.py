"""This stream, for the end credits: who followed, subbed, gifted, raided,
cheered, chatted for the first time, which mods were there, and a few stats.

Filled in by the alerts as they happen (MixItUp's URLs, nothing extra to set
up), plus /credits/seen/<user>?role=mod for mods and VIPs. MixItUp's Stream
Start event calls /credits/reset, which starts a new list. Saved to the
config folder, so a restart mid-stream doesn't lose it.
"""
import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger("vibetv.session")

# The credits sections, in the order they roll.
SECTIONS = ["mods", "vips", "raiders", "subs", "resubs", "gifts", "cheers", "streaks",
            "follows", "first_chatters", "gigantify", "hype", "stats"]
PEOPLE_SECTIONS = [s for s in SECTIONS if s not in ("hype", "stats")]
MAX_PER_SECTION = 300
MAX_RECIPIENTS = 60


class Session:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.empty()
        self.on_change = None           # called after every change (the server refreshes open credits pages)
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text("utf-8"))
                if isinstance(loaded, dict) and isinstance(loaded.get("people"), dict):
                    self.data = self.empty() | loaded
                    for s in PEOPLE_SECTIONS:
                        self.data["people"].setdefault(s, [])
        except Exception as e:
            log.warning("stream session file unreadable, starting a new one: %s", e)

    @staticmethod
    def empty():
        return {"started": int(time.time()), "people": {s: [] for s in PEOPLE_SECTIONS}, "hype_level": 0}

    # ── changes ──
    def reset(self):
        self.data = self.empty()
        self.changed()

    def changed(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data), "utf-8")
            os.replace(tmp, self.path)
        except OSError as e:
            log.warning("couldn't save the stream session: %s", e)
        if self.on_change:
            self.on_change()

    def _person(self, section, user):
        """The entry for this person in this section (made if new), or None if the section is full."""
        login = (user.get("login") or user.get("display_name") or "").lower()
        if not login:
            return None
        people = self.data["people"][section]
        for p in people:
            if p["login"] == login:
                p["name"] = user.get("display_name") or p["name"]
                p["avatar"] = user.get("avatar") or p.get("avatar", "")
                return p
        if len(people) >= MAX_PER_SECTION:
            return None
        p = {"login": login, "name": user.get("display_name") or login, "avatar": user.get("avatar") or ""}
        people.append(p)
        return p

    def seen(self, user, role):
        """/credits/seen/<user>?role=mod|vip: they were here this stream."""
        section = {"mod": "mods", "vip": "vips"}.get(role)
        if section and self._person(section, user):
            self.changed()

    def record(self, kind, payload):
        """An alert that played (payload: what the screens got, with the
        person already looked up on Twitch)."""
        user = payload.get("user") or {}
        p = None
        if kind == "follow":
            p = self._person("follows", user)
        elif kind == "sub":
            p = self._person("subs", user)
            if p and payload.get("tier"):
                p["tier"] = payload["tier"]
        elif kind == "resub":
            p = self._person("resubs", user)
            if p:
                p["months"] = max(p.get("months") or 0, payload.get("months") or 0) or None
                if payload.get("tier"):
                    p["tier"] = payload["tier"]
        elif kind == "gift":
            p = self._person("gifts", user)
            if p:
                p["count"] = (p.get("count") or 0) + (payload.get("count") or 0)
                have = {r["login"] for r in p.setdefault("to", [])}
                for r in payload.get("recipients") or []:
                    login = (r.get("login") or "").lower()
                    if login and login not in have and len(p["to"]) < MAX_RECIPIENTS:
                        p["to"].append({"login": login, "name": r.get("display_name") or login, "avatar": r.get("avatar") or ""})
                        have.add(login)
        elif kind == "bits":
            p = self._person("cheers", user)
            if p:
                p["amount"] = (p.get("amount") or 0) + (payload.get("amount") or 0)
        elif kind == "raid":
            p = self._person("raiders", user)
            if p:
                p["viewers"] = (p.get("viewers") or 0) + (payload.get("viewers") or 0)
        elif kind == "streak":
            p = self._person("streaks", user)
            if p:
                p["count"] = max(p.get("count") or 0, payload.get("count") or 0)
        elif kind == "welcome":
            p = self._person("first_chatters", user)
        elif kind == "gigantify":
            p = self._person("gigantify", user)
            emote = payload.get("emote") or {}
            if p and emote.get("url"):
                emotes = p.setdefault("emotes", [])
                if emote["url"] not in emotes:
                    emotes.append(emote["url"])
                    del emotes[:-4]                 # their last few
        if p is not None:
            self.changed()

    def hype(self, level):
        if level and level > self.data.get("hype_level", 0):
            self.data["hype_level"] = level
            self.changed()

    # ── what the credits page gets ──
    def snapshot(self):
        people = self.data["people"]
        stats = {
            "follows": len(people["follows"]),
            "subs": len(people["subs"]) + len(people["resubs"]),
            "gifted": sum(p.get("count") or len(p.get("to") or []) for p in people["gifts"]),
            "raids": len(people["raiders"]),
            "raiders": sum(p.get("viewers") or 0 for p in people["raiders"]),
            "bits": sum(p.get("amount") or 0 for p in people["cheers"]),
            "first_chatters": len(people["first_chatters"]),
        }
        return {"started": self.data["started"], "people": people,
                "hype_level": self.data.get("hype_level", 0), "stats": stats}
