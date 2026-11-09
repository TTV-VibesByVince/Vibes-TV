"""Arcade games for the BRB screen: one command each, once every 5 seconds per person.

  Plinko        !drop    a coin bounces down the pegs into a slot (the edges pay 500)
  Coin pusher   !push    drop a coin on the pile; coins pushed off the edge are yours
  Boss fight    !hit     beat the boss together; the final blow gets the spotlight
  Piñata        !whack   it breaks after a secret number of whacks
  Sumo arena    !join, then !bump to charge the nearest rival; last one in the ring wins
  Tower stack   !stack   drop a block from the swinging crane; don't topple the tower

The server decides every result, so OBS and the TV always show the same thing.
The coin pusher and sumo arena move things around, so the server runs their
physics (step(), 20 times a second) and sends the positions (frame()) to the
screens, which draw them. Positions are in the screen's own units: the game
area is 940 x 698.
"""
import math

COOLDOWN = 5                    # seconds between one person's commands
PALETTE = ["#ff2a6d", "#9146ff", "#ff8a3d", "#3ddc84", "#4d7bff", "#b483ff", "#ffc34d", "#ff7aa5",
           "#2fc9a5", "#e5283a", "#c08bff", "#ffa94d"]
EVENT_SECONDS = 8               # how long things to animate stay in the snapshot


def color_for(login):
    """The same colour for the same person every time."""
    return PALETTE[sum(ord(c) * (i + 1) for i, c in enumerate(login)) % len(PALETTE)]


def mini(who):
    return {"login": who["login"], "name": who["name"], "avatar": who.get("avatar") or "", "c": color_for(who["login"])}


class Arcade:
    kind = ""
    cmds = ()
    frames = False              # True: has physics, step() and frame()

    def __init__(self, clock, rng, feed):
        self.clock, self.rng, self.feed = clock, rng, feed
        self.last = {}          # login -> when they last played
        self.scores = {}        # login -> {..., "n"}: the leaderboard, for this whole break
        self.events = []
        self.seq = 0
        self.start()

    def start(self):
        """A fresh game (the leaderboard carries on)."""
        self.events = []

    def handle(self, who, text):
        """A chat message. True if it did something."""
        word = (text.split() or [""])[0].lower()
        if word not in self.cmds:
            return False
        now = self.clock()
        if now - self.last.get(who["login"], -999) < COOLDOWN:
            return False
        if not self.play(mini(who), word):
            return False
        self.last[who["login"]] = now
        return True

    def play(self, who, cmd):
        raise NotImplementedError

    def tick(self, now):
        """Every second. True if the screen should update."""
        return False

    def event(self, **e):
        now = self.clock()
        self.seq += 1
        e.update(id=self.seq, t=now)
        self.events.append(e)
        self.events = [x for x in self.events if now - x["t"] < EVENT_SECONDS][-60:]

    def score(self, who, n):
        s = self.scores.setdefault(who["login"], {**who, "n": 0})
        s["n"] += n

    def top(self, k=5):
        return sorted(self.scores.values(), key=lambda s: -s["n"])[:k]

    def view(self):
        now = self.clock()
        return {"scores": self.top(), "events": [e for e in self.events if now - e["t"] < EVENT_SECONDS]}

    def awards(self):
        return []


# ── Plinko ──────────────────────────────────────────────────────────────
PLINKO_ROWS = 8
PLINKO_SLOTS = [500, 50, 10, 3, 1, 3, 10, 50, 500]
PLINKO_FALL = 2.6               # seconds a coin takes to reach its slot on screen


class Plinko(Arcade):
    kind = "plinko"
    cmds = ("!drop",)

    def start(self):
        super().start()
        self.pending = []       # coins still falling: scored when they land

    def play(self, who, cmd):
        path = [self.rng.choice((-1, 1)) for _ in range(PLINKO_ROWS)]
        slot = (sum(path) + PLINKO_ROWS) // 2
        pts = PLINKO_SLOTS[slot]
        self.event(kind="drop", who=who, path=path, slot=slot, pts=pts)
        self.pending.append((self.clock() + PLINKO_FALL, who, pts))
        return True

    def tick(self, now):
        landed = [p for p in self.pending if p[0] <= now]
        if not landed:
            return False
        self.pending = [p for p in self.pending if p[0] > now]
        for _, who, pts in landed:
            self.score(who, pts)
            self.feed(who, "hit the 500 jackpot" if pts >= 500 else f"scored {pts}")
        return True

    def awards(self):
        best = self.top(1)
        return [{"label": "Plinko high score", "text": f"{best[0]['name']} · {best[0]['n']}"}] if best else []


# ── Boss fight ──────────────────────────────────────────────────────────
BOSSES = ["Grumbo the Lag Monster", "Sir Buffers-a-Lot", "The Ping Goblin", "Queen Disconnecta",
          "Dropped Frame Fred", "Captain Cooldown"]
BOSS_HP = 800                   # the first boss; each one after is 60% tougher
BOSS_DOWN = 5                   # seconds before the next boss turns up


class Boss(Arcade):
    kind = "boss"
    cmds = ("!hit", "!attack")

    def __init__(self, *a):
        self.n = 0
        self.kills = {}
        super().__init__(*a)

    def start(self):
        super().start()
        self.spawn()

    def spawn(self):
        self.n += 1
        self.max = int(round(BOSS_HP * 1.6 ** (self.n - 1), -1))
        self.hp = self.max
        self.name = BOSSES[(self.n - 1) % len(BOSSES)]
        self.down_until = None
        self.killer = None

    def play(self, who, cmd):
        if self.down_until:
            return False
        crit = self.rng.random() < .1
        dmg = self.rng.randint(10, 60) * (3 if crit else 1)
        self.hp = max(0, self.hp - dmg)
        self.score(who, dmg)
        self.event(kind="hit", who=who, d=dmg, crit=crit)
        if self.hp <= 0:
            self.killer = who
            k = self.kills.setdefault(who["login"], {**who, "n": 0})
            k["n"] += 1
            self.down_until = self.clock() + BOSS_DOWN
            self.event(kind="ko", who=who)
            self.feed(who, f"beat {self.name}")
        else:
            self.feed(who, f"landed a {dmg} crit" if crit else f"hit for {dmg}")
        return True

    def tick(self, now):
        if self.down_until and now >= self.down_until:
            self.spawn()
            return True
        return False

    def view(self):
        return {**super().view(), "boss": self.name, "hp": self.hp, "max": self.max, "n": self.n,
                "down": bool(self.down_until), "killer": self.killer}

    def awards(self):
        if self.kills:
            k = max(self.kills.values(), key=lambda x: x["n"])
            return [{"label": "Boss slayer", "text": f"{k['name']} · {k['n']} final blow{'' if k['n'] == 1 else 's'}"}]
        best = self.top(1)
        return [{"label": "Top boss damage", "text": f"{best[0]['name']} · {best[0]['n']}"}] if best else []


# ── Piñata ──────────────────────────────────────────────────────────────
PINATA_MIN, PINATA_MAX = 20, 40     # whacks it takes (secret, different every time)
PINATA_DOWN = 5


class Pinata(Arcade):
    kind = "pinata"
    cmds = ("!whack", "!swing")

    def __init__(self, *a):
        self.num = 0
        self.breaks = {}
        super().__init__(*a)

    def start(self):
        super().start()
        self.new()

    def new(self):
        self.num += 1
        self.need = self.rng.randint(PINATA_MIN, PINATA_MAX)
        self.n = 0
        self.broke_until = None
        self.breaker = None

    def play(self, who, cmd):
        if self.broke_until:
            return False
        self.n += 1
        self.score(who, 1)
        if self.n >= self.need:
            self.breaker = who
            b = self.breaks.setdefault(who["login"], {**who, "n": 0})
            b["n"] += 1
            self.broke_until = self.clock() + PINATA_DOWN
            self.event(kind="break", who=who)
            self.feed(who, "broke the piñata")
        else:
            self.event(kind="whack", who=who)
            self.feed(who, "whacked it")
        return True

    def tick(self, now):
        if self.broke_until and now >= self.broke_until:
            self.new()
            return True
        return False

    def view(self):
        return {**super().view(), "crack": round(min(1, self.n / self.need), 1), "broke": bool(self.broke_until),
                "breaker": self.breaker, "num": self.num}

    def awards(self):
        if not self.breaks:
            return []
        b = max(self.breaks.values(), key=lambda x: x["n"])
        return [{"label": "Piñata smasher", "text": b["name"] + (f" · {b['n']} broken" if b["n"] > 1 else "")}]


# ── Tower stack ─────────────────────────────────────────────────────────
TOWER_BW = 170                  # block width (the screen draws them 40 high)
TOWER_CENTER = 470
TOWER_DOWN = 3.5                # seconds the fallen tower stays down


def crane_x(height, t):
    """Where the crane is: it swings wider and faster as the tower grows."""
    return TOWER_CENTER + min(280, 50 + height * 14) * math.sin(t * (1 + height * .04))


class Tower(Arcade):
    kind = "tower"
    cmds = ("!stack",)

    def __init__(self, *a):
        self.best = 0
        self.best_by = None
        super().__init__(*a)

    def start(self):
        super().start()
        self.t0 = self.clock()
        self.stack = []
        self.fell_until = None

    def play(self, who, cmd):
        if self.fell_until:
            return False
        level = len(self.stack)
        x = round(crane_x(level, self.clock() - self.t0), 1)
        if self.stack and abs(x - self.stack[-1]["x"]) > TOWER_BW / 2:
            self.event(kind="slide", who=who, x=x, level=level)
            self.feed(who, "slid off the edge")
            return True
        self.stack.append({"x": x, **who})
        self.score(who, 1)
        if len(self.stack) > self.best:
            self.best, self.best_by = len(self.stack), who
        for i in range(len(self.stack) - 2, -1, -1):        # does the tower above any block lean past its edge?
            above = self.stack[i + 1:]
            com = sum(b["x"] for b in above) / len(above)
            if abs(com - self.stack[i]["x"]) > TOWER_BW / 2:
                height = len(self.stack)
                gone = self.stack[i + 1:]
                del self.stack[i + 1:]
                self.fell_until = self.clock() + TOWER_DOWN
                self.event(kind="topple", who=who, x=x, level=level, gone=gone, at=i + 1, height=height,
                           dir=1 if com > self.stack[i]["x"] else -1)
                self.feed(who, f"knocked it over at {height}")
                return True
        self.event(kind="stack", who=who, x=x, level=level)
        self.feed(who, f"stacked block {level + 1}")
        return True

    def tick(self, now):
        if self.fell_until and now >= self.fell_until:
            self.stack = []
            self.fell_until = None
            return True
        return False

    def view(self):
        return {**super().view(), "stack": self.stack, "t0": self.t0, "fell": bool(self.fell_until),
                "best": self.best, "best_by": self.best_by}

    def awards(self):
        if not self.best:
            return []
        return [{"label": "Tallest tower", "text": f"{self.best} block{'' if self.best == 1 else 's'} · top by {self.best_by['name']}"}]


# ── physics helpers ─────────────────────────────────────────────────────
def owners_table(items, key):
    """Compact frames: each thing points at a short list of the people in it."""
    owners, index = [], {}
    for it in items:
        who = it.get(key)
        if who and who["login"] not in index:
            index[who["login"]] = len(owners)
            owners.append([who["c"], who["name"], who["avatar"]])
    return owners, index


# ── Coin pusher ─────────────────────────────────────────────────────────
PUSH_L, PUSH_R, PUSH_EDGE = 110, 830, 640
COIN_R, PRIZE_R = 24, 36
PRIZE_VALUE = 25
PRIZE_EVERY = 20                # seconds before a new gold star after one is won


def pusher_y(t):
    """The bottom edge of the sliding shelf."""
    return 150 + (math.sin(t * 1.2) + 1) * 90


class Pusher(Arcade):
    kind = "pusher"
    cmds = ("!push", "!coin")
    frames = True

    def start(self):
        super().start()
        self.t0 = self.clock()
        self.py = pusher_y(0)
        self.coins = []
        self.cid = 0
        self.last_by = None
        for _ in range(95):            # a full tray, so a push carries through the pile to the edge
            self.add(self.rng.uniform(PUSH_L + COIN_R, PUSH_R - COIN_R), self.rng.uniform(300, PUSH_EDGE - 4))
        self.add(470, 470, prize=True)
        self.prize_due = None
        for _ in range(30):
            self.relax()

    def add(self, x, y, who=None, prize=False):
        self.cid += 1
        self.coins.append({"id": self.cid, "x": x, "y": y, "who": who, "prize": prize})

    def play(self, who, cmd):
        self.add(self.rng.uniform(PUSH_L + 60, PUSH_R - 60), self.py + COIN_R + 4, who)
        self.last_by = who
        self.feed(who, "dropped a coin")
        return True

    def relax(self):
        """Push overlapping coins apart (the shelf only pushes, it never moves back)."""
        cells = {}
        for c in self.coins:
            cells.setdefault((int(c["x"] // 72), int(c["y"] // 72)), []).append(c)
        for (cx, cy), group in cells.items():
            near = [o for dx in (-1, 0, 1) for dy in (-1, 0, 1) for o in cells.get((cx + dx, cy + dy), ())]
            for a in group:
                ra = PRIZE_R if a["prize"] else COIN_R
                for b in near:
                    if b["id"] <= a["id"]:
                        continue
                    m = ra + (PRIZE_R if b["prize"] else COIN_R)
                    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                    d = math.hypot(dx, dy)
                    if d >= m or d < .01:
                        continue
                    push, nx, ny = (m - d) / 2, dx / d, dy / d
                    wa = 0 if a["y"] < self.py + 40 else 1          # coins against the shelf don't move back
                    wb = 0 if b["y"] < self.py + 40 else 1
                    if wa + wb == 0:
                        wa = wb = 1
                    a["x"] -= nx * push * wa * 2 / (wa + wb)
                    a["y"] -= ny * push * wa * 2 / (wa + wb)
                    b["x"] += nx * push * wb * 2 / (wa + wb)
                    b["y"] += ny * push * wb * 2 / (wa + wb)
        for c in self.coins:
            r = PRIZE_R if c["prize"] else COIN_R
            c["x"] = max(PUSH_L + r, min(PUSH_R - r, c["x"]))
            c["y"] = max(self.py + r, c["y"])

    def step(self, dt):
        now = self.clock()
        self.py = pusher_y(now - self.t0)
        for _ in range(5):
            self.relax()
        kept = []
        for c in self.coins:
            if c["y"] <= PUSH_EDGE + 6:
                kept.append(c)
                continue
            who = self.last_by
            if who:
                v = PRIZE_VALUE if c["prize"] else 1
                self.score(who, v)
                self.event(kind="win", who=who, x=round(c["x"]), v=v)
                if c["prize"]:
                    self.feed(who, "won the gold star")
            if c["prize"]:
                self.prize_due = now + PRIZE_EVERY
        self.coins = kept
        if len(self.coins) < 85 and self.rng.random() < dt * .5:          # the machine tops itself up a bit
            self.add(self.rng.uniform(PUSH_L + 60, PUSH_R - 60), self.py + COIN_R + 4)
        if self.prize_due and now >= self.prize_due:
            self.prize_due = None
            self.add(self.rng.uniform(300, 640), self.py + PRIZE_R + 4, prize=True)

    def frame(self):
        owners, index = owners_table(self.coins, "who")
        return {"py": round(self.py, 1), "owners": owners,
                "coins": [[c["id"], round(c["x"], 1), round(c["y"], 1), -2 if c["prize"] else index[c["who"]["login"]] if c["who"] else -1]
                          for c in self.coins]}

    def view(self):
        return {**super().view(), "t0": self.t0}

    def awards(self):
        best = self.top(1)
        return [{"label": "Most coins pushed", "text": f"{best[0]['name']} · {best[0]['n']} coins"}] if best else []


# ── Sumo arena ──────────────────────────────────────────────────────────
SUMO_CX, SUMO_CY = 470, 420
SUMO_RING, SUMO_RING_MIN = 250, 110
SUMO_BLOB = 32
SUMO_JOIN = 25                  # seconds to !join before a match
SUMO_MAX = 16
SUMO_WON = 6                    # seconds the winner is shown


class Sumo(Arcade):
    kind = "sumo"
    cmds = ("!join", "!bump")
    frames = True

    def __init__(self, *a):
        self.match = 0
        self.wins = {}
        super().__init__(*a)

    def start(self):
        super().start()
        self.new_match()

    def new_match(self):
        self.match += 1
        self.phase = "join"
        self.until = self.clock() + SUMO_JOIN
        self.blobs = []
        self.ring = SUMO_RING
        self.winner = None

    def handle(self, who, text):
        word = (text.split() or [""])[0].lower()
        if word == "!join" and self.phase != "join":        # don't spend the cooldown on a !join that can't count
            return False
        return super().handle(who, text)

    def play(self, who, cmd):
        if cmd == "!join":
            if len(self.blobs) >= SUMO_MAX or any(b["who"]["login"] == who["login"] for b in self.blobs):
                return False
            a, r = self.rng.uniform(0, 2 * math.pi), self.rng.uniform(0, SUMO_RING * .6)
            self.blobs.append({"who": who, "x": SUMO_CX + math.cos(a) * r, "y": SUMO_CY + math.sin(a) * r * .7,
                               "vx": 0.0, "vy": 0.0, "out": False})
            self.feed(who, "jumped in the ring")
            return True
        me = next((b for b in self.blobs if b["who"]["login"] == who["login"] and not b["out"]), None)
        if self.phase != "fight" or not me:
            return False
        rivals = [b for b in self.blobs if not b["out"] and b is not me]
        if not rivals:
            return False
        o = min(rivals, key=lambda b: math.hypot(b["x"] - me["x"], b["y"] - me["y"]))
        d = math.hypot(o["x"] - me["x"], o["y"] - me["y"]) or 1
        me["vx"] += (o["x"] - me["x"]) / d * 9
        me["vy"] += (o["y"] - me["y"]) / d * 9
        self.event(kind="bump", who=who)
        self.feed(who, "charged " + o["who"]["name"])
        return True

    def tick(self, now):
        if self.phase == "join" and now >= self.until:
            if len(self.blobs) >= 2:
                self.phase = "fight"
            else:
                self.until = now + 10                       # not enough people yet: wait a bit longer
            return True
        if self.phase == "won" and now >= self.until:
            self.new_match()
            return True
        return False

    def step(self, dt):
        k = dt * 60                                         # the numbers below are per 1/60 s
        live = [b for b in self.blobs if not b["out"]]
        if self.phase == "fight":
            self.ring = max(SUMO_RING_MIN, self.ring - 9 * dt)
            wobble = .02 if self.ring > SUMO_RING_MIN else .05
            for b in live:
                if self.rng.random() < wobble * k:
                    b["vx"] += self.rng.uniform(-3, 3)
                    b["vy"] += self.rng.uniform(-3, 3)
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                d = math.hypot(dx, dy)
                if d >= SUMO_BLOB * 2 or d < .1:
                    continue
                nx, ny = dx / d, dy / d
                rv = (a["vx"] - b["vx"]) * nx + (a["vy"] - b["vy"]) * ny
                if rv > 0:
                    a["vx"] -= rv * nx * 1.1
                    a["vy"] -= rv * ny * 1.1
                    b["vx"] += rv * nx * 1.1
                    b["vy"] += rv * ny * 1.1
                o = (SUMO_BLOB * 2 - d) / 2
                a["x"] -= nx * o
                a["y"] -= ny * o
                b["x"] += nx * o
                b["y"] += ny * o
        damp = .96 ** k
        for b in live:
            b["x"] += b["vx"] * k
            b["y"] += b["vy"] * k
            b["vx"] *= damp
            b["vy"] *= damp
            ex, ey = (b["x"] - SUMO_CX) / self.ring, (b["y"] - SUMO_CY) / (self.ring * .7)
            dist = math.hypot(ex, ey)
            if self.phase == "fight" and dist > 1.08:
                b["out"], b["out_at"] = True, self.clock()
                self.event(kind="out", who=b["who"])
                self.feed(b["who"], "got bumped out")
            elif self.phase != "fight" and dist > .9:
                b["x"] = SUMO_CX + (b["x"] - SUMO_CX) * .9 / dist
                b["y"] = SUMO_CY + (b["y"] - SUMO_CY) * .9 / dist
        if self.phase == "fight":
            live = [b for b in self.blobs if not b["out"]]
            if len(live) <= 1:
                champ = live[0] if live else max(self.blobs, key=lambda b: b.get("out_at", 0))     # all out at once: the last one out
                champ["out"] = False
                self.winner = champ["who"]
                w = self.wins.setdefault(self.winner["login"], {**self.winner, "n": 0})
                w["n"] += 1
                self.score(self.winner, 1)
                self.phase, self.until = "won", self.clock() + SUMO_WON
                self.event(kind="win", who=self.winner)
                self.feed(self.winner, "won the sumo match")

    def frame(self):
        owners, index = owners_table(self.blobs, "who")
        return {"ring": round(self.ring, 1), "phase": self.phase, "owners": owners,
                "blobs": [[index[b["who"]["login"]], round(b["x"], 1), round(b["y"], 1), 1 if b["out"] else 0] for b in self.blobs]}

    def view(self):
        return {**super().view(), "phase": self.phase, "until": self.until, "match": self.match,
                "alive": sum(1 for b in self.blobs if not b["out"]), "joined": len(self.blobs), "winner": self.winner}

    def awards(self):
        if not self.wins:
            return []
        w = max(self.wins.values(), key=lambda x: x["n"])
        return [{"label": "Sumo champ", "text": f"{w['name']} · {w['n']} win{'' if w['n'] == 1 else 's'}"}]


ARCADE = {g.kind: g for g in (Plinko, Pusher, Boss, Pinata, Sumo, Tower)}
