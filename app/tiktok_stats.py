"""TikTok LIVE counts for the widgets: total likes, who liked the most, who
gifted the most (in coins), and how many are watching.

Starts over when a new TikTok live begins (a new room), or with the Reset
button / /tiktok/reset. Saved to the config folder, so a restart mid-stream
keeps the counts.
"""
import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger("vibetv.tiktok")

MAX_PEOPLE = 5000          # people tracked per list (the widgets show the top 10)
SAVE_EVERY = 5.0           # seconds between saves while likes pour in


class TikTokStats:
    def __init__(self, path):
        self.path = Path(path)
        self.on_change = None           # the server pushes new numbers to the widgets
        self.live = False
        self.saved_at = 0.0
        self.data = self.empty()
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text("utf-8"))
                if isinstance(loaded, dict) and isinstance(loaded.get("likers"), dict):
                    self.data = self.empty() | loaded
        except Exception as e:
            log.warning("TikTok counts file unreadable, starting over: %s", e)

    @staticmethod
    def empty(room=None):
        return {"room": room, "started": int(time.time()), "likes": 0, "viewers": 0,
                "likers": {}, "gifters": {}}

    # ── changes ──
    def changed(self, force_save=False):
        now = time.monotonic()
        if force_save or now - self.saved_at > SAVE_EVERY:
            self.saved_at = now
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.data), "utf-8")
                os.replace(tmp, self.path)
            except OSError as e:
                log.warning("couldn't save the TikTok counts: %s", e)
        if self.on_change:
            self.on_change()

    def reset(self, room=None):
        self.data = self.empty(room)
        self.changed(force_save=True)

    def new_live(self, room):
        """Connected to a live: a different room than last time means a new stream."""
        if room and str(room) != str(self.data.get("room")):
            self.reset(str(room))

    def set_live(self, live):
        if live != self.live:
            self.live = live
            if self.on_change:
                self.on_change()

    def _bump(self, table, who, field, amount):
        key = (who.get("user") or who.get("display") or "").lower()
        if not key or amount <= 0:
            return
        people = self.data[table]
        p = people.get(key)
        if p is None:
            if len(people) >= MAX_PEOPLE:
                return
            p = people[key] = {"name": who.get("display") or key, "avatar": who.get("avatar") or "", field: 0}
        else:
            p["name"] = who.get("display") or p["name"]
            p["avatar"] = who.get("avatar") or p.get("avatar", "")
        p[field] = p.get(field, 0) + amount

    def like(self, who, count, total=None):
        """count: likes in this burst. total: the live's total, when TikTok sends it."""
        count = max(0, int(count or 0))
        self._bump("likers", who, "likes", count)
        self.data["likes"] = max(self.data["likes"] + count, int(total or 0))
        self.changed()

    def gift(self, who, coins):
        self._bump("gifters", who, "coins", max(0, int(coins or 0)))
        self.changed()

    def viewers(self, count):
        count = max(0, int(count or 0))
        if count != self.data["viewers"]:
            self.data["viewers"] = count
            self.changed()

    # ── what the widgets get ──
    def top(self, table, field, n):
        people = sorted(self.data[table].values(), key=lambda p: -p.get(field, 0))[:n]
        return [{"name": p["name"], "avatar": p.get("avatar", ""), field: p.get(field, 0)} for p in people]

    def snapshot(self, n=10):
        return {"likes": self.data["likes"], "viewers": self.data["viewers"], "live": self.live,
                "likers": self.top("likers", "likes", n), "gifters": self.top("gifters", "coins", n)}
