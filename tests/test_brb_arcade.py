"""The BRB arcade games: one command each, the server decides every result."""
import random

import brb as B
import brb_arcade as A
from test_brb import make, p


def arcade(kind, seed=1):
    """One arcade game on its own, with a clock the test moves."""
    clock = [1000.0]
    fed = []
    game = A.ARCADE[kind](lambda: clock[0], random.Random(seed), lambda who, what: fed.append((who["login"], what)))
    return game, clock, fed


def test_cooldown_and_commands():
    game, clock, _ = arcade("plinko")
    assert not game.handle(p("ann"), "drop")                # needs the !
    assert game.handle(p("ann"), "!drop please")
    assert not game.handle(p("ann"), "!drop")               # 5 s each
    clock[0] += A.COOLDOWN
    assert game.handle(p("ann"), "!DROP")
    assert len(game.view()["events"]) == 2


def test_plinko_scores_when_the_coin_lands():
    game, clock, fed = arcade("plinko")
    game.handle(p("ann"), "!drop")
    drop = game.events[-1]
    assert sum(drop["path"]) == drop["slot"] * 2 - A.PLINKO_ROWS and drop["pts"] == A.PLINKO_SLOTS[drop["slot"]]
    assert game.top() == [] and not game.tick(clock[0] + 1)          # still falling
    assert game.tick(clock[0] + A.PLINKO_FALL)
    assert game.top()[0]["n"] == drop["pts"] and fed
    assert game.awards()[0]["label"] == "Plinko high score"


def test_boss_fight_final_blow_and_next_boss():
    game, clock, fed = arcade("boss")
    first = game.max
    hitters = [p(f"p{i}") for i in range(200)]
    for who in hitters:
        if game.down_until:
            break
        game.handle(who, "!hit")
    assert game.hp == 0 and game.killer and game.view()["down"]
    assert not game.handle(p("late"), "!hit")                 # the boss is down
    assert ("p" in fed[-1][0]) and "beat" in fed[-1][1]
    game.tick(clock[0] + A.BOSS_DOWN)
    assert game.n == 2 and game.max > first and game.hp == game.max
    assert game.awards()[0]["label"] == "Boss slayer"


def test_pinata_breaks_at_its_secret_number():
    game, clock, fed = arcade("pinata")
    need = game.need
    assert A.PINATA_MIN <= need <= A.PINATA_MAX
    for i in range(need):
        assert game.handle(p(f"p{i}"), "!whack")
    assert game.view()["broke"] and game.breaker["login"] == f"p{need - 1}" and game.view()["crack"] == 1
    game.tick(clock[0] + A.PINATA_DOWN)
    assert game.num == 2 and game.n == 0
    assert game.awards()[0]["text"].startswith(f"P{need - 1}")


def test_tower_stacks_slides_and_topples():
    game, clock, fed = arcade("tower")
    # drop when the crane is dead centre: sin(0) = 0
    clock[0] = game.t0
    assert game.handle(p("ann"), "!stack") and game.stack[-1]["x"] == A.TOWER_CENTER
    # next block, a little to the right: it stacks
    game.t0 = clock[0] = clock[0] + 10
    game.t0 -= 0.5
    assert game.handle(p("bob"), "!stack")
    assert len(game.stack) == 2 and game.events[-1]["kind"] == "stack"
    # far past the edge of the top block: it slides off
    x = lambda h, t: A.crane_x(h, t)                          # noqa: E731
    t = next(t / 100 for t in range(1, 400) if abs(x(2, t / 100) - game.stack[-1]["x"]) > A.TOWER_BW / 2 + 5)
    clock[0] += 10
    game.t0 = clock[0] - t
    assert game.handle(p("cat"), "!stack") and game.events[-1]["kind"] == "slide" and len(game.stack) == 2


def test_tower_topples_when_it_leans_too_far():
    game, clock, fed = arcade("tower")
    game.stack = [{"x": 400, **A.mini(p("a"))}, {"x": 470, **A.mini(p("b"))}]
    # a block at 530 sits on the one below it (60 off), but the top two then average 500: past the bottom block's edge (485)
    t = next(t / 1000 for t in range(1, 4000) if abs(A.crane_x(2, t / 1000) - 530) < 1)
    game.t0 = clock[0] - t
    assert game.handle(p("cat"), "!stack")
    e = game.events[-1]
    assert e["kind"] == "topple" and e["height"] == 3 and len(game.stack) == 1 and game.view()["fell"]
    assert not game.handle(p("dan"), "!stack")                # it's down
    game.tick(clock[0] + A.TOWER_DOWN)
    assert game.stack == [] and game.best == 3


def test_coin_pusher_runs_and_scores_the_last_dropper():
    game, clock, fed = arcade("pusher", seed=3)
    for i in range(30):
        game.handle(p(f"p{i}"), "!push")
        for _ in range(10):
            clock[0] += .05
            game.step(.05)
    frame = game.frame()
    assert frame["coins"] and all(len(c) == 4 for c in frame["coins"])
    assert all(A.PUSH_L <= c[1] <= A.PUSH_R and c[2] >= frame["py"] for c in frame["coins"])
    assert game.top(), "something should have been pushed off in 15 seconds"
    assert game.top()[0]["login"].startswith("p")


def test_sumo_join_fight_and_winner():
    game, clock, fed = arcade("sumo", seed=2)
    assert not game.handle(p("ann"), "!bump")                 # no match yet
    for name in ("ann", "bob", "cat", "dan"):
        assert game.handle(p(name), "!join")
    assert not game.handle(p("ann"), "!join")                 # cooldown, and already in
    clock[0] += A.SUMO_JOIN
    game.tick(clock[0])
    assert game.phase == "fight"
    assert not game.handle(p("eve"), "!join")                 # too late for this match
    for _ in range(20 * 120):
        clock[0] += .05
        game.step(.05)
        if game.phase == "won":
            break
    assert game.phase == "won" and game.winner and game.view()["alive"] == 1
    assert game.awards()[0]["label"] == "Sumo champ"
    game.tick(clock[0] + A.SUMO_WON)
    assert game.phase == "join" and game.match == 2 and game.blobs == []


def test_in_a_break_vote_shows_four_and_awards_reach_the_recap():
    g, clock = make(brb_mode="one", brb_games={k: False for k in ("paint", "trivia", "typing", "polls")})
    g.start()
    assert g.snapshot()["game"]["kind"] == "plinko"
    g.chat(p("ann"), "!drop")
    assert g.snapshot()["game"]["events"]
    clock.go(A.PLINKO_FALL + 1, g)
    assert g.snapshot()["game"]["scores"][0]["login"] == "ann"
    g.back()
    assert g.snapshot()["recap"]["awards"][0]["label"] == "Plinko high score"

    g, clock = make()
    g.start()
    opts = g.snapshot()["game"]["options"]
    assert len(opts) == B.VOTE_OPTIONS and len({o["key"] for o in opts}) == 4


def test_physics_only_for_pusher_and_sumo():
    g, clock = make(brb_mode="one", brb_games={k: False for k in ("paint", "trivia", "typing", "polls", "plinko")})
    g.start()
    assert g.snapshot()["game"]["kind"] == "pusher" and g.physics()
    g.step(.05)
    assert g.frame()["kind"] == "pusher" and g.frame()["coins"]
    g2, _ = make(brb_mode="one", brb_games={k: False for k in ("paint", "trivia", "typing", "polls")})
    g2.start()
    assert g2.physics() is None and g2.frame() is None


def test_arcade_game_ends_and_moves_on():
    g, clock = make(brb_mode="turns", brb_arcade_minutes=1, brb_games={k: False for k in ("paint", "trivia", "typing", "polls")})
    g.start()
    assert g.snapshot()["game"]["kind"] == "plinko"
    clock.go(61, g)
    assert g.snapshot()["game"]["kind"] == "pusher"
