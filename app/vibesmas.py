"""The Vibesmas Express: a holiday train for alerts, and a video when a hype train starts.

Between two dates (Settings > Vibesmas, 11-25 to 12-31 to start with) follows,
subs, gift subs, bits and raids roll across the screen as a train instead of
a card: the locomotive says what happened, and each passenger car carries a
person. The server works out the whole train here (which cars, what they say,
how long it takes to pass) so the TV and the overlay draw the same thing and
the alert queue knows how long to wait. vibesmas.js draws it.
"""
import re
import struct
import time

TRAIN_KINDS = ("follow", "sub", "resub", "gift", "bits", "raid")
MAX_CARS = 10                   # gift subs: one car each, up to this many

# car widths in screen units (the screen is 1920 wide); vibesmas.js draws them at these sizes
WIDTHS = {"loco": 440, "tender": 240, "coach": 270, "crowd": 250, "coal": 240, "caboose": 250}
SCREEN = 1920
SHORT_SECONDS = 8.2             # a train that fits stops in the middle: in 2 s, stops, out 2.4 s
CRAWL = 440                     # a long train crawls past at this speed (units a second)

DATE_RE = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def active(settings, today=None):
    """Is it Vibesmas? "on", "off", or between the two dates (which may wrap the new year)."""
    mode = settings["vibesmas"]
    if mode in ("on", "off"):
        return mode == "on"
    a, b = settings["vibesmas_from"], settings["vibesmas_to"]
    if not (DATE_RE.match(a) and DATE_RE.match(b)):
        return False
    md = time.strftime("%m-%d", today or time.localtime())
    return (a <= md <= b) if a <= b else (md >= a or md <= b)


def banner_width(text):
    return min(640, 80 + len(text) * 12) + 70


def person(p):
    return {"name": p.get("display_name") or p.get("login") or "Someone", "avatar": p.get("avatar") or "",
            "login": p.get("login") or ""}


def count_text(n, one, many):
    return f"{n:,} {one if n == 1 else many}"


def train_for(kind, payload):
    """The cars for one alert, front to back, with the train's length and running time."""
    who = person(payload["user"])
    cars = []
    if kind == "follow":
        cars = [{"car": "loco", "label": "NEW FOLLOW"}, {"car": "tender"}, {"car": "coach", "who": who, "sub": "ALL ABOARD!"}]
    elif kind in ("sub", "resub"):
        tier, months = payload.get("tier_level") or 1, payload.get("months")
        sub = " · ".join(x for x in [f"{months} MONTHS" if months and int(months) > 1 else "", f"TIER {tier}" if tier > 1 else ""] if x)
        cars = [{"car": "loco", "label": "RESUB" if kind == "resub" else "NEW SUB"}, {"car": "tender"},
                {"car": "coach", "who": who, "sub": sub or "WELCOME ABOARD", "first": tier >= 3}]
    elif kind == "gift":
        count = max(int(payload.get("count") or 0), len(payload.get("recipients") or []), 1)
        riders = (payload.get("recipients") or [])[:MAX_CARS]
        gifter = who["name"].upper()
        cars = [{"car": "loco", "label": count_text(count, "GIFT SUB", "GIFT SUBS")}, {"car": "tender"},
                {"car": "coach", "who": who, "sub": f"GIFTED {count_text(count, 'SUB', 'SUBS')}", "first": True}]
        cars += [{"car": "coach", "who": person(r), "sub": f"GIFT FROM {gifter}"[:26]} for r in riders]
        more = count - len(riders)
        if more > 0:
            cars.append({"car": "caboose", "text": f"+{more:,} PASSENGER{'' if more == 1 else 'S'}", "sub": "ALSO ABOARD"})
    elif kind == "bits":
        amount = int(payload.get("amount") or 0)
        cars = [{"car": "loco", "label": f"{amount:,} BITS"}, {"car": "tender"}, {"car": "coach", "who": who, "sub": f"CHEERED {amount:,}"}]
        cars += [{"car": "coal", "amount": amount}] * (1 if amount < 1000 else 2 if amount < 10000 else 3)
    elif kind == "raid":
        viewers = int(payload.get("viewers") or 0)
        cars = [{"car": "loco", "label": "RAID!"}, {"car": "tender"},
                {"car": "coach", "who": who, "sub": f"RAIDING WITH {viewers:,}" if viewers else "RAIDING", "first": True}]
        cars += [{"car": "crowd"}] * (1 if viewers < 20 else 2 if viewers < 100 else 3)
        cars.append({"car": "caboose", "text": count_text(viewers, "PASSENGER", "PASSENGERS") if viewers else "ALL ABOARD"})
    if not cars or cars[-1]["car"] != "caboose":
        cars.append({"car": "caboose", "text": "HAPPY VIBESMAS"})
    message = ((payload.get("text") or {}).get("message") or "").strip()
    if message and kind in ("sub", "resub", "bits"):
        cars.append({"car": "banner", "text": message[:60]})
    length = sum(banner_width(c["text"]) if c["car"] == "banner" else WIDTHS[c["car"]] for c in cars)
    return {"cars": cars, "length": length, "seconds": seconds_for(length)}


def seconds_for(length):
    """A short train rolls in, stops for the bell, rolls out; a long one crawls the whole way."""
    if length <= SCREEN - 320:
        return SHORT_SECONDS
    return round(2.6 + (SCREEN + 40 + length + 80) / CRAWL, 1)


def mp4_seconds(path):
    """How long an .mp4/.mov is, from its movie header (no ffmpeg needed). None if unreadable."""
    try:
        with open(path, "rb") as f:
            data = f.read(64 * 1024 * 1024)
    except OSError:
        return None
    i = data.find(b"mvhd")
    if i < 4:
        return None
    version = data[i + 4]
    try:
        if version == 1:
            scale, dur = struct.unpack(">IQ", data[i + 24:i + 36])
        else:
            scale, dur = struct.unpack(">II", data[i + 16:i + 24])
    except struct.error:
        return None
    return round(dur / scale, 2) if scale else None


def webm_seconds(path):
    """How long a .webm is, from its Segment Info (Duration x TimecodeScale). None if unreadable."""
    try:
        with open(path, "rb") as f:
            data = f.read(1024 * 1024)
    except OSError:
        return None
    if not data.startswith(b"\x1a\x45\xdf\xa3"):
        return None
    scale = 1_000_000                                   # the default: milliseconds
    i = data.find(b"\x2a\xd7\xb1")
    if i >= 0 and 0x81 <= data[i + 3] <= 0x88:
        n = data[i + 3] & 0x0F
        scale = int.from_bytes(data[i + 4:i + 4 + n], "big") or scale
    i = data.find(b"\x44\x89\x88")
    fmt, n = ">d", 8
    if i < 0:
        i, fmt, n = data.find(b"\x44\x89\x84"), ">f", 4
    if i < 0 or len(data) < i + 3 + n:
        return None
    ticks = struct.unpack(fmt, data[i + 3:i + 3 + n])[0]
    secs = ticks * scale / 1e9
    return round(secs, 2) if secs > 0 else None


def video_seconds(path):
    """How long a video is (.mp4/.mov/.m4v or .webm). None if unreadable."""
    return webm_seconds(path) if str(path).lower().endswith(".webm") else mp4_seconds(path)
