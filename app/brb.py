"""Be right back: games for chat while you're away.

You start it (Settings, /brb/start, or a mod's !brb) and the BRB screen shows
"Be right back" with a countdown. Chat plays while you're gone, reading
Twitch chat (Connect Twitch):

  Guess when I'm back  runs the whole time: !guess 8:42 (one guess each)
  Chat paints          !paint C4 pink on a 26 x 15 grid, every 5 s each
  Trivia               10 questions about you: pick 1 to 4 (multiple choice), or
                       type the answer (first right answer scores)
  Typing race          8 sentences, first three to type each one score
  This or that         10 polls, 1 or 2, one vote each
  Arcade games         Plinko, coin pusher, boss fight, piñata, sumo arena and
                       tower stack: one command each (see brb_arcade.py)

Between games chat votes for the next one, from 4 picked at random (or they
take turns, or one game repeats). When you're back (I'm back, /brb/back or !back) the screen shows
what chat got up to, then goes away.

Nothing here touches the network or the clock directly: the server feeds it
chat messages and calls tick() every second; the tests pass their own clock.
"""
import random
import re
import time

from brb_arcade import ARCADE

GAMES = ["paint", "trivia", "typing", "polls", "plinko", "pusher", "boss", "pinata", "sumo", "tower"]   # the games chat picks between
GAME_NAMES = {"vote": "Chat picks the next game", "guess": "Guess when I'm back", "paint": "Chat paints a picture", "trivia": "Trivia",
              "typing": "Typing race", "polls": "This or that", "plinko": "Plinko", "pusher": "Coin pusher",
              "boss": "Boss fight", "pinata": "Piñata", "sumo": "Sumo arena", "tower": "Tower stack"}
GAME_BLURBS = {"paint": "Build a picture together, one pixel at a time", "trivia": "Who knows {name} best?",
               "typing": "Fastest fingers win", "polls": "Pick a side, 10 questions",
               "plinko": "Drop coins, chase the 500 jackpot", "pusher": "Shove coins off the edge",
               "boss": "Beat the boss together", "pinata": "Whack it till it breaks",
               "sumo": "Last one in the ring wins", "tower": "Build it high, don't knock it over"}
MODES = ("vote", "turns", "one")
VOTE_OPTIONS = 4            # games on each vote, picked at random

VOTE_SECONDS = 20
TRIVIA_SECONDS = 20
TYPING_SECONDS = 30
REVEAL_SECONDS = 5
POLL_PAUSE = 3
PER_ROUND = 10              # trivia and this-or-that questions per game
MAX_WRONG = 3               # wrong answers per multiple-choice question (4 options at most)
TYPING_ROUNDS = 8
TYPING_WINNERS = 3
PAINT_COOLDOWN = 5
PAINT_W, PAINT_H = 26, 15   # A-Z by 1-15
FEED_SIZE = 8

COLORS = {"pink": "#ff2a6d", "purple": "#9146ff", "gold": "#ffc34d", "green": "#3ddc84", "orange": "#ff8a3d",
          "white": "#f6f2ff", "blue": "#4d7bff", "red": "#e5283a", "black": "#0b0910"}
COLOR_ALIASES = {"yellow": "gold", "violet": "purple", "magenta": "pink", "grey": "white", "gray": "white"}
ERASE = ("erase", "clear", "none")

GUESS_RE = re.compile(r"^!guess\s+(\d{1,3})(?:[:.](\d{1,2}))?\b", re.I)
PAINT_RE = re.compile(r"^!paint\s+(?:([a-z])\s*(\d{1,2})\s+([a-z]+)|([a-z]+)\s+([a-z])\s*(\d{1,2}))\s*$", re.I)
COMMAND_RE = re.compile(r"^!(brb|back)\b\s*(\d{1,3})?", re.I)


def norm(text):
    """Lower case, punctuation as spaces, single spaces: what answers are compared on."""
    text = (text or "").lower().replace("'", "").replace("’", "")
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def parse_trivia(raw, name):
    """Question = answers | what the screen shows [| wrong | wrong | wrong]
    With wrong answers it's multiple choice: the shown answer is the right option."""
    out = []
    for line in (raw or "").splitlines():
        if "=" not in line:
            continue
        q, rest = line.split("=", 1)
        answers, *more = rest.split("|")
        accepted = [a for a in (norm(a) for a in answers.split(",")) if a]
        q = q.strip().replace("{name}", name)
        if q and accepted:
            shown = (more[0].strip() if more else "") or answers.split(",")[0].strip()
            wrong = [w.strip() for w in more[1:] if w.strip() and norm(w) != norm(shown)][:MAX_WRONG]
            item = {"q": q, "accept": accepted, "shown": shown}
            if wrong:
                item["wrong"] = wrong
            out.append(item)
    return out


def parse_polls(raw):
    out = []
    for line in (raw or "").splitlines():
        if "|" not in line:
            continue
        left, b = line.split("|", 1)
        title, _, a = left.rpartition(":")
        a, b = a.strip(), b.strip()
        if a and b:
            out.append({"title": title.strip() + "?" if title.strip() else "", "a": a, "b": b})
    return out


def parse_lines(raw):
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def fmt(secs):
    secs = max(0, int(secs))
    return f"{secs // 60}:{secs % 60:02d}"


class BRB:
    def __init__(self, settings, clock=time.time, rng=None):
        self.S = settings
        self.clock = clock
        self.rng = rng or random.Random()
        self.on_change = None           # called after anything the screen should show changes
        self.on_painting = None         # called with the finished painting when you're back
        self.name = lambda: "the streamer"
        self.used = {"trivia": set(), "polls": set(), "typing": set()}     # asked this server run
        self.st = None

    # ── starting and stopping ──
    @property
    def phase(self):
        return self.st["phase"] if self.st else "idle"

    def start(self, minutes=None):
        """Start (or restart the countdown of) a break."""
        minutes = max(1, min(120, int(minutes or self.S["brb_minutes"] or 10)))
        now = self.clock()
        if self.phase == "away":
            self.st["minutes"] = minutes
            self.st["ends"] = now + minutes * 60
            self.changed()
            return
        self.st = {"phase": "away", "started": now, "minutes": minutes, "ends": now + minutes * 60,
                   "back_at": None, "recap_until": None, "guesses": {}, "feed": [],
                   "canvas": [""] * (PAINT_W * PAINT_H), "painters": {}, "paint_last": {},
                   "trivia": {}, "typing": {}, "polls": [], "played": [], "game": None, "turn": 0, "arcade": {}}
        self.next_game()
        self.changed()

    def back(self):
        if self.phase != "away":
            return False
        now = self.clock()
        self.st.update(phase="back", back_at=now, recap_until=now + max(10, int(self.S["brb_recap_seconds"] or 45)),
                       game=None)
        if self.on_painting and any(self.st["canvas"]):
            self.on_painting(self.painting())
        self.changed()
        return True

    def stop(self):
        """Hide the BRB screen straight away."""
        self.st = None
        self.changed()

    def changed(self):
        if self.on_change:
            self.on_change()

    # ── which game is next ──
    def enabled(self, game):
        return self.S["brb_games"].get(game, True)

    def playable(self):
        out = []
        for g in GAMES:
            if not self.enabled(g):
                continue
            if g == "trivia" and not self.bank("trivia"):
                continue
            if g == "polls" and not self.bank("polls"):
                continue
            if g == "typing" and not self.bank("typing"):
                continue
            out.append(g)
        return out

    def bank(self, kind):
        if kind == "trivia":
            return parse_trivia(self.S["brb_trivia"], self.name())
        if kind == "polls":
            return parse_polls(self.S["brb_polls"])
        return parse_lines(self.S["brb_typing"])

    def draw(self, kind, n):
        """n questions from a bank, none repeated until the whole bank has been asked."""
        items = self.bank(kind)
        keys = [str(x) for x in items]
        fresh = [i for i, k in enumerate(keys) if k not in self.used[kind]]
        if len(fresh) < n:
            self.used[kind] = set()
            fresh = list(range(len(items)))
        self.rng.shuffle(fresh)
        picked = fresh[:n]
        self.used[kind].update(keys[i] for i in picked)
        return [items[i] for i in picked]

    def next_game(self):
        games = self.playable()
        st = self.st
        if not games:
            st["game"] = None
            return
        mode = self.S["brb_mode"] if self.S["brb_mode"] in MODES else "vote"
        if mode == "one":
            self.begin(games[0])
        elif mode == "turns" or len(games) == 1:
            self.begin(games[st["turn"] % len(games)])
            st["turn"] += 1
        else:
            pool = [g for g in games if not st["played"] or g != st["played"][-1]] if len(games) > VOTE_OPTIONS else games
            options = self.rng.sample(pool, min(VOTE_OPTIONS, len(pool)))
            options.sort(key=games.index)
            st["game"] = {"kind": "vote", "options": options, "votes": {}, "ends": self.clock() + VOTE_SECONDS}

    def begin(self, kind):
        now = self.clock()
        g = {"kind": kind}
        if kind == "paint":
            g["ends"] = now + max(1, int(self.S["brb_paint_minutes"] or 3)) * 60
        elif kind == "trivia":
            g.update(items=self.draw("trivia", PER_ROUND), i=-1)
        elif kind == "typing":
            g.update(items=self.draw("typing", TYPING_ROUNDS), i=-1)
        elif kind == "polls":
            g.update(items=self.draw("polls", PER_ROUND), i=-1)
        elif kind in ARCADE:
            g["ends"] = now + max(1, int(self.S["brb_arcade_minutes"] or 3)) * 60
            game = self.st["arcade"].get(kind)
            if game:
                game.start()                        # a fresh board, same leaderboard
            else:
                game = self.st["arcade"][kind] = ARCADE[kind](self.clock, self.rng, self.feed)
            g["arcade"] = game
        self.st["game"] = g
        self.st["played"].append(kind)
        if kind not in ARCADE and kind != "paint":
            self.next_item()

    def next_item(self):
        g, now = self.st["game"], self.clock()
        g["i"] += 1
        if g["i"] >= len(g["items"]):
            self.next_game()
            return
        g["reveal"] = None
        if g["kind"] == "trivia":
            g["ends"] = now + TRIVIA_SECONDS
            item = g["items"][g["i"]]
            if item.get("wrong"):                   # multiple choice: shuffle the options, everyone picks once
                options = [item["shown"]] + item["wrong"]
                self.rng.shuffle(options)
                g.update(options=options, correct=options.index(item["shown"]), picks={})
            else:
                g.update(options=None, correct=None, picks={})
        elif g["kind"] == "typing":
            g.update(ends=now + TYPING_SECONDS, started=now, done=[])
        else:
            poll_secs = max(10, min(60, int(self.S["brb_poll_seconds"] or 35)))
            g.update(ends=now + poll_secs, votes={})

    # ── time passing ──
    def tick(self):
        if not self.st:
            return
        now = self.clock()
        if self.phase == "back":
            if now >= self.st["recap_until"]:
                self.st = None
                self.changed()
            return
        g = self.st["game"]
        if g and "arcade" in g and now < g["ends"]:
            if g["arcade"].tick(now):
                self.changed()
            return
        if not g or now < g["ends"]:
            return
        if g["kind"] == "vote":
            counts = {o: 0 for o in g["options"]}
            for o in g["votes"].values():
                counts[o] += 1
            top = max(counts.values())
            self.begin(self.rng.choice([o for o, c in counts.items() if c == top]))
        elif g["kind"] == "paint" or "arcade" in g:
            self.next_game()
        elif g.get("reveal") is not None:           # the answer has been shown long enough
            self.next_item()
        else:
            self.reveal(g, now)
        self.changed()

    def reveal(self, g, now):
        item = g["items"][g["i"]]
        if g["kind"] == "trivia" and g.get("options"):
            counts = [0] * len(g["options"])
            right = []
            for login, (pick, who) in g["picks"].items():
                counts[pick] += 1
                if pick == g["correct"]:
                    right.append(who)
                    score = self.st["trivia"].setdefault(login, {**who, "n": 0})
                    score["n"] += 1
            g["reveal"] = {"answer": item["shown"], "correct": g["correct"], "counts": counts,
                           "right": len(right), "firsts": right[:3]}
            g["ends"] = now + REVEAL_SECONDS
        elif g["kind"] == "trivia":
            g["reveal"] = {"answer": item["shown"], "winner": None}
            g["ends"] = now + REVEAL_SECONDS
        elif g["kind"] == "typing":
            g["reveal"] = {"done": list(g["done"])}
            g["ends"] = now + REVEAL_SECONDS
        else:
            va = sum(1 for v in g["votes"].values() if v == 0)
            vb = len(g["votes"]) - va
            self.st["polls"].append({"title": item["title"], "a": item["a"], "b": item["b"], "va": va, "vb": vb})
            g["reveal"] = {"va": va, "vb": vb}
            g["ends"] = now + POLL_PAUSE

    # ── chat ──
    def command(self, text, is_mod):
        """!brb [minutes] and !back, for you and your mods. True if it did something."""
        m = COMMAND_RE.match(text.strip())
        if not m or not is_mod:
            return False
        if m.group(1).lower() == "brb":
            self.start(m.group(2))
            return True
        return self.back()

    def chat(self, user, text):
        """A chat message while you're away. user: {"login", "name", "avatar"}"""
        if self.phase != "away":
            return
        text = (text or "").strip()
        login = (user.get("login") or "").lower()
        if not login or not text:
            return
        who = {"login": login, "name": user.get("name") or login, "avatar": user.get("avatar") or ""}
        if self.guess(who, text):
            return
        g = self.st["game"]
        if not g:
            return
        if "arcade" in g:
            if g["arcade"].handle(who, text):
                self.changed()
            return
        handled = {"vote": self.vote, "paint": self.paint, "trivia": self.answer, "typing": self.typed,
                   "polls": self.poll_vote}[g["kind"]](g, who, text)
        if handled:
            self.changed()

    def feed(self, who, what):
        self.st["feed"].insert(0, {**who, "what": what})
        del self.st["feed"][FEED_SIZE:]

    def guess(self, who, text):
        m = GUESS_RE.match(text)
        if not m:
            return False
        if not self.enabled("guess") or who["login"] in self.st["guesses"]:
            return True
        secs = int(m.group(1)) * 60 + int(m.group(2) or 0)
        if int(m.group(2) or 0) > 59 or secs <= self.clock() - self.st["started"] or secs > 180 * 60:
            return True                             # already past, or nonsense
        self.st["guesses"][who["login"]] = {**who, "secs": secs}
        self.feed(who, "guessed " + fmt(secs))
        self.changed()
        return True

    def vote(self, g, who, text):
        if not text.isdigit() or who["login"] in g["votes"]:
            return False
        n = int(text) - 1
        if not 0 <= n < len(g["options"]):
            return False
        g["votes"][who["login"]] = g["options"][n]
        self.feed(who, "voted " + GAME_NAMES[g["options"][n]])
        return True

    def paint(self, g, who, text):
        m = PAINT_RE.match(text)
        if not m:
            return False
        col, row, color = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(5), m.group(6), m.group(4))
        color = COLOR_ALIASES.get(color.lower(), color.lower())
        x, y = ord(col.lower()) - 97, int(row) - 1
        if not (0 <= x < PAINT_W and 0 <= y < PAINT_H) or (color not in COLORS and color not in ERASE):
            return False
        now = self.clock()
        if now - self.st["paint_last"].get(who["login"], -999) < PAINT_COOLDOWN:
            return False
        self.st["paint_last"][who["login"]] = now
        self.st["canvas"][y * PAINT_W + x] = "" if color in ERASE else color
        p = self.st["painters"].setdefault(who["login"], {**who, "n": 0})
        p["n"] += 1
        self.feed(who, f"painted {col.upper()}{row} {color}")
        return True

    def answer(self, g, who, text):
        if g.get("reveal") is not None:
            return False
        if g.get("options"):
            return self.choose(g, who, text)
        item = g["items"][g["i"]]
        said = f" {norm(text)} "
        if not any(f" {a} " in said for a in item["accept"]):
            return False
        score = self.st["trivia"].setdefault(who["login"], {**who, "n": 0})
        score["n"] += 1
        g["reveal"] = {"answer": item["shown"], "winner": who}
        g["ends"] = self.clock() + REVEAL_SECONDS
        self.feed(who, "got it right")
        return True

    def choose(self, g, who, text):
        """Multiple choice: 1 to 4 (or the option itself). The first pick counts; the answer
        shows when time's up."""
        if who["login"] in g["picks"]:
            return False
        said = norm(text)
        pick = int(said) - 1 if said.isdigit() else next((i for i, o in enumerate(g["options"]) if norm(o) == said), -1)
        if not 0 <= pick < len(g["options"]):
            return False
        g["picks"][who["login"]] = (pick, who)     # in the order they came in: the first right ones get named
        self.feed(who, "locked in an answer")
        return True

    def typed(self, g, who, text):
        if g.get("reveal") is not None or any(d["login"] == who["login"] for d in g["done"]):
            return False
        if norm(text) != norm(g["items"][g["i"]]):
            return False
        secs = round(self.clock() - g["started"], 1)
        g["done"].append({**who, "secs": secs})
        best = self.st["typing"].get(who["login"])
        if not best or secs < best["secs"]:
            self.st["typing"][who["login"]] = {**who, "secs": secs}
        self.feed(who, f"typed it in {secs:.1f} s")
        if len(g["done"]) >= TYPING_WINNERS:
            self.reveal(g, self.clock())
        return True

    def poll_vote(self, g, who, text):
        if g.get("reveal") is not None or who["login"] in g["votes"]:
            return False
        item, said = g["items"][g["i"]], norm(text)
        pick = 0 if said in ("1", norm(item["a"])) else 1 if said in ("2", norm(item["b"])) else None
        if pick is None:
            return False
        g["votes"][who["login"]] = pick
        self.feed(who, "voted " + (item["a"] if pick == 0 else item["b"]))
        return True

    # ── physics (coin pusher, sumo arena): the server steps it 20 times a second ──
    def physics(self):
        """The arcade game that needs stepping, if one is on."""
        g = self.st and self.st["phase"] == "away" and self.st["game"]
        return g["arcade"] if g and "arcade" in g and g["arcade"].frames else None

    def step(self, dt):
        game = self.physics()
        if game:
            n = len(game.events)
            game.step(dt)
            if len(game.events) != n:               # something scored or fell out
                self.changed()

    def frame(self):
        game = self.physics()
        return {"kind": game.kind, "now": self.clock(), **game.frame()} if game else None

    # ── what the screen gets ──
    def painting(self):
        top = sorted(self.st["painters"].values(), key=lambda p: -p["n"])[:3]
        return {"w": PAINT_W, "h": PAINT_H, "cells": [COLORS.get(c, "") for c in self.st["canvas"]],
                "painters": [{"name": p["name"], "avatar": p["avatar"], "n": p["n"]} for p in top]}

    def snapshot(self, twitch_live=True):
        now = self.clock()
        if not self.st:
            return {"phase": "idle", "now": now, "name": self.name(), "twitch": twitch_live}
        st = self.st
        out = {"phase": st["phase"], "now": now, "name": self.name(), "twitch": twitch_live,
               "started": st["started"], "ends": st["ends"], "minutes": st["minutes"],
               "feed": st["feed"], "guess_on": self.enabled("guess"),
               "guesses": sorted(st["guesses"].values(), key=lambda g: g["secs"]), "game": None}
        g = st["game"]
        if g and st["phase"] == "away":
            out["game"] = self.game_view(g)
        if st["phase"] == "back":
            out["recap"] = self.recap()
        return out

    def game_view(self, g):
        kind = g["kind"]
        v = {"kind": kind, "name": GAME_NAMES[kind], "ends": g["ends"]}
        if kind == "vote":
            v["options"] = [{"key": o, "name": GAME_NAMES[o], "blurb": GAME_BLURBS[o].replace("{name}", self.name()),
                             "votes": sum(1 for x in g["votes"].values() if x == o)} for o in g["options"]]
        elif kind == "paint":
            v.update(self.painting())
            v["colors"] = COLORS
        elif kind in ARCADE:
            v.update(g["arcade"].view())
        else:
            v.update(n=g["i"] + 1, of=len(g["items"]), reveal=g.get("reveal"))
            item = g["items"][g["i"]]
            if kind == "trivia":
                v["q"] = item["q"]
                if g.get("options"):
                    v.update(options=g["options"], picked=len(g["picks"]))
                v["scores"] = sorted(self.st["trivia"].values(), key=lambda s: -s["n"])[:3]
            elif kind == "typing":
                v.update(text=item, done=g["done"], started=g["started"])
            else:
                va = sum(1 for x in g["votes"].values() if x == 0)
                v.update(title=item["title"], a=item["a"], b=item["b"], va=va, vb=len(g["votes"]) - va)
                nxt = g["items"][g["i"] + 1] if g["i"] + 1 < len(g["items"]) else None
                v["next"] = f"{nxt['a']} or {nxt['b']}" if nxt else None
        return v

    def recap(self):
        st = self.st
        away = st["back_at"] - st["started"]
        winner = None
        if st["guesses"]:
            w = min(st["guesses"].values(), key=lambda g: abs(g["secs"] - away))
            winner = {**w, "off": int(round(abs(w["secs"] - away)))}
        best = lambda d, key, rev: (sorted(d.values(), key=lambda x: x[key], reverse=rev) or [None])[0]   # noqa: E731
        return {"away": int(away), "guess": winner, "guesses": len(st["guesses"]),
                "trivia": best(st["trivia"], "n", True), "typing": best(st["typing"], "secs", False),
                "painter": best(st["painters"], "n", True),
                "painting": self.painting() if any(st["canvas"]) else None,
                "polls": st["polls"], "played": len(st["played"]),
                "awards": [a for game in st["arcade"].values() for a in game.awards()]}
