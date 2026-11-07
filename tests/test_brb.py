"""Be right back: the games chat plays while you're away."""
import random

import pytest

import brb as B
import twitch_live as tl

TRIVIA = """What was the first game {name} streamed? = fortnite | Fortnite
What's {name}'s go-to pizza? = pepperoni | Pepperoni pizza with a side of ranch
Skipped question? =
Where did {name} grow up? = phoenix
Favourite fast food? = in n out, innout | In-N-Out
Favourite emote? = vibesb5stretch, stretch
"""


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def go(self, secs, game=None):
        """Let time pass a second at a time, as the server does."""
        for _ in range(int(secs)):
            self.t += 1
            if game:
                game.tick()


def make(**over):
    S = {"brb_minutes": 10, "brb_games": {}, "brb_mode": "vote", "brb_paint_minutes": 3, "brb_poll_seconds": 35,
         "brb_recap_seconds": 45, "brb_trivia": TRIVIA, "brb_polls": "Coke | Pepsi\nPineapple on pizza: Yes | No\n" +
         "\n".join(f"A{i} | B{i}" for i in range(20)), "brb_typing": "Six sticky skeletons\nToy boat toy boat\nRed lorry"}
    S.update(over)
    clock = Clock()
    g = B.BRB(S, clock=clock, rng=random.Random(4))
    g.name = lambda: "Vince"
    return g, clock


def p(name):
    return {"login": name, "name": name.capitalize(), "avatar": ""}


def test_banks_parse():
    t = B.parse_trivia(TRIVIA, "Vince")
    assert len(t) == 5                                              # the one with no answer isn't asked
    assert t[0]["q"] == "What was the first game Vince streamed?" and t[1]["shown"].startswith("Pepperoni pizza")
    assert t[3]["accept"] == ["in n out", "innout"] and t[2]["shown"] == "phoenix"
    polls = B.parse_polls("Coke | Pepsi\nPineapple on pizza: Yes | No\nnot a poll")
    assert polls == [{"title": "", "a": "Coke", "b": "Pepsi"}, {"title": "Pineapple on pizza?", "a": "Yes", "b": "No"}]
    assert B.norm("In-N-Out!!") == "in n out" and B.norm("Reese's") == "reeses"


def test_start_countdown_and_vote():
    g, clock = make()
    g.start()
    snap = g.snapshot()
    assert snap["phase"] == "away" and snap["ends"] - snap["started"] == 600
    assert snap["game"]["kind"] == "vote" and [o["key"] for o in snap["game"]["options"]] == B.GAMES
    g.chat(p("ann"), "2")
    g.chat(p("ann"), "3")                                           # one vote each
    g.chat(p("bob"), "2")
    g.chat(p("cat"), "4")
    assert [o["votes"] for o in g.snapshot()["game"]["options"]] == [0, 2, 0, 1]
    clock.go(B.VOTE_SECONDS, g)
    assert g.snapshot()["game"]["kind"] == "trivia"


def test_guess_and_welcome_back():
    g, clock = make()
    seen = []
    g.on_painting = seen.append
    g.start(5)
    g.chat(p("ann"), "!guess 8:42")
    g.chat(p("ann"), "!guess 9:00")                                 # one guess each
    g.chat(p("bob"), "!guess 9")
    g.chat(p("cat"), "!guess 0:30")                                 # already past? not yet: 30 s in the future
    clock.go(60, g)
    g.chat(p("dan"), "!guess 0:45")                                 # already past: ignored
    assert [x["login"] for x in g.snapshot()["guesses"]] == ["cat", "ann", "bob"]
    clock.go(9 * 60 - 60 + 5, g)                                    # back after 9:05
    assert g.back()
    recap = g.snapshot()["recap"]
    assert recap["away"] == 545 and recap["guess"]["login"] == "bob" and recap["guess"]["off"] == 5
    assert not seen                                                 # nothing painted, nothing for the credits
    clock.go(46, g)
    assert g.phase == "idle"


def test_mods_start_and_end_it_from_chat():
    g, clock = make()
    assert not g.command("!brb 5", False)                           # not a mod
    assert g.command("!brb 5", True) and g.st["minutes"] == 5
    assert g.command("!back", True) and g.phase == "back"
    assert not g.command("hello", True)


def test_trivia_round():
    g, clock = make(brb_mode="one", brb_games={"paint": False})
    g.start()
    v = g.snapshot()["game"]
    assert v["kind"] == "trivia" and v["n"] == 1 and v["of"] == 5      # the whole bank is 5 here (10 max)
    q = g.st["game"]["items"][0]
    g.chat(p("ann"), "no idea")
    g.chat(p("bob"), "I think it's " + q["accept"][0] + "!")
    v = g.snapshot()["game"]
    assert v["reveal"]["winner"]["login"] == "bob" and v["reveal"]["answer"] == q["shown"]
    g.chat(p("cat"), q["accept"][0])                                # too late
    assert v["scores"][0]["n"] == 1 and len(v["scores"]) == 1
    clock.go(B.REVEAL_SECONDS, g)
    assert g.snapshot()["game"]["n"] == 2
    clock.go(B.TRIVIA_SECONDS, g)                                   # nobody got it: the answer shows anyway
    assert g.snapshot()["game"]["reveal"]["winner"] is None
    clock.go(B.REVEAL_SECONDS + 3 * (B.TRIVIA_SECONDS + B.REVEAL_SECONDS), g)    # questions 3 to 5 nobody gets
    assert g.snapshot()["game"]["kind"] == "trivia" and g.snapshot()["game"]["n"] == 1   # "just one": round two


def test_questions_dont_repeat_until_all_asked():
    g, clock = make()
    first = [x["a"] for x in g.draw("polls", 10)]
    second = [x["a"] for x in g.draw("polls", 10)]
    assert len(set(first)) == 10 and not set(first) & set(second)


def test_polls_round_and_results():
    g, clock = make(brb_mode="one", brb_games={"paint": False, "trivia": False, "typing": False}, brb_poll_seconds=30)
    g.start()
    v = g.snapshot()["game"]
    assert v["kind"] == "polls" and v["of"] == 10
    g.chat(p("ann"), "1")
    g.chat(p("ann"), "2")                                           # one vote each
    g.chat(p("bob"), "2")
    g.chat(p("cat"), v["b"].lower())                                # the option's name works too
    assert (g.snapshot()["game"]["va"], g.snapshot()["game"]["vb"]) == (1, 2)
    clock.go(30, g)
    assert g.snapshot()["game"]["reveal"] == {"va": 1, "vb": 2}
    clock.go(B.POLL_PAUSE, g)
    assert g.snapshot()["game"]["n"] == 2
    g.back()
    assert g.snapshot()["recap"]["polls"][0] == {"title": v["title"], "a": v["a"], "b": v["b"], "va": 1, "vb": 2}


def test_typing_race():
    g, clock = make(brb_mode="one", brb_games={"paint": False, "trivia": False})
    g.start()
    text = g.snapshot()["game"]["text"]
    clock.go(3, g)
    g.chat(p("ann"), text.upper() + "!")                            # case and punctuation don't matter
    g.chat(p("ann"), text)
    g.chat(p("bob"), text + " typo")
    clock.go(1, g)
    g.chat(p("cat"), text)
    g.chat(p("dan"), text)                                          # third to finish: the round is over
    v = g.snapshot()["game"]
    assert [d["login"] for d in v["done"]] == ["ann", "cat", "dan"] and v["reveal"] is not None
    assert v["done"][0]["secs"] == 3.0


def test_painting_and_the_credits():
    g, clock = make(brb_mode="one")
    pics = []
    g.on_painting = pics.append
    g.start()
    assert g.snapshot()["game"]["kind"] == "paint"
    g.chat(p("ann"), "!paint C4 pink")
    g.chat(p("ann"), "!paint D4 pink")                              # 5 s between pixels
    clock.go(5, g)
    g.chat(p("ann"), "!paint gold d4")                              # either order
    g.chat(p("bob"), "!paint Z15 purple")
    g.chat(p("cat"), "!paint Z16 purple")                           # off the canvas
    g.chat(p("dan"), "!paint A1 teal")                              # not a colour
    cells = g.snapshot()["game"]["cells"]
    assert cells[3 * 26 + 2] == B.COLORS["pink"] and cells[3 * 26 + 3] == B.COLORS["gold"]
    assert cells[14 * 26 + 25] == B.COLORS["purple"] and sum(1 for c in cells if c) == 3
    g.back()
    assert pics and pics[0]["painters"][0]["name"] == "Ann" and pics[0]["painters"][0]["n"] == 2
    assert g.snapshot()["recap"]["painting"]["cells"] == cells


def test_chat_from_twitch():
    ev = {"broadcaster_user_id": "1", "broadcaster_user_login": "vibesbyvince", "chatter_user_login": "ann",
          "chatter_user_name": "Ann", "badges": [{"set_id": "subscriber"}], "message": {"text": "!guess 8:42"}}
    assert tl.translate("channel.chat.message", ev) == [
        ("chat", {"user": {"login": "ann", "name": "Ann", "avatar": ""}, "text": "!guess 8:42", "mod": False})]
    ev.update(chatter_user_login="vibesbyvince", chatter_user_name="VibesByVince", badges=[])
    assert tl.translate("channel.chat.message", ev)[0][1]["mod"] is True       # you


# ── through the server ───────────────────────────────────────────────────

async def test_brb_urls_and_page(client, srv):
    ws = await client.ws_connect("/ws?screen=brb&preview=1")
    await ws.receive_json()
    first = await ws.receive_json()
    assert first["type"] == "brb" and first["data"]["phase"] == "idle"
    assert (await client.get("/brb")).status == 200
    assert (await client.get("/brb/start?minutes=abc")).status == 400
    r = await (await client.get("/brb/start?minutes=7")).json()
    assert r["ok"] and r["minutes"] == 7
    msg = await ws.receive_json(timeout=3)
    assert msg["type"] == "brb" and msg["data"]["phase"] == "away" and msg["data"]["ends"] - msg["data"]["started"] == 420
    assert (await (await client.get("/brb/back")).json())["was_away"] is True
    assert srv.brb.phase == "back"
    await client.get("/brb/stop")
    assert srv.brb.phase == "idle"
    await ws.close()
    srv.brb.stop()


async def test_tv_shows_it(client, srv, tv):
    await client.get("/brb/start")
    assert (await tv.next("brb_show"))["on"] is True
    await client.get("/brb/stop")
    assert (await tv.next("brb_show"))["on"] is False


async def test_chat_plays_through_twitch(client, srv, monkeypatch):
    async def profile(who):
        return {"login": who["login"], "display_name": who["name"], "avatar": ""}
    monkeypatch.setattr(srv, "profile_for", profile)
    chat = lambda login, text, badge="subscriber": {   # noqa: E731
        "broadcaster_user_id": "1", "broadcaster_user_login": "vibesbyvince", "chatter_user_login": login,
        "chatter_user_name": login, "badges": [{"set_id": badge}], "message": {"text": text}}
    await srv.twitch_live.handle("channel.chat.message", chat("ann", "!brb"))          # not a mod: nothing
    assert srv.brb.phase == "idle"
    await srv.twitch_live.handle("channel.chat.message", chat("modone", "!brb 3", "moderator"))
    assert srv.brb.phase == "away" and srv.brb.st["minutes"] == 3
    await srv.twitch_live.handle("channel.chat.message", chat("ann", "!guess 2:30"))
    assert "ann" in srv.brb.st["guesses"]
    await srv.twitch_live.handle("channel.chat.message", chat("vibesbyvince", "!back", "broadcaster"))
    assert srv.brb.phase == "back"
    srv.brb.stop()


async def test_brb_settings(client, srv):
    r = await client.post("/api/settings", json={"brb_mode": "turns", "brb_minutes": "15", "brb_games": {"paint": False, "x": False},
                                                 "brb_poll_seconds": 40})
    assert r.status == 200
    assert srv.S["brb_mode"] == "turns" and srv.S["brb_minutes"] == 15 and srv.S["brb_games"] == {"paint": False}
    assert (await client.post("/api/settings", json={"brb_mode": "chaos"})).status == 400
    assert (await client.post("/api/settings", json={"brb_poll_seconds": 5})).status == 400
    state = await (await client.get("/api/state")).json()
    assert state["brb_games"][0] == "guess" and state["status"]["brb"]["phase"] == "idle"
    assert state["status"]["brb"]["polls_ready"] == 45


@pytest.mark.parametrize("cells", [["#ff2a6d"] + [""] * 389])
def test_painting_in_the_credits(srv, cells):
    srv.session.painting({"w": 26, "h": 15, "cells": cells, "painters": []})
    assert srv.session.snapshot()["painting"]["cells"][0] == "#ff2a6d"
    assert "painting" in srv.credits_info()["sections"]
    srv.session.reset()
    assert srv.session.snapshot()["painting"] is None
