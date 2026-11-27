"""TikTok events running MixItUp commands, against a pretend MixItUp."""
import asyncio

import pytest
from aiohttp import web

FOLLOW_ID = "11111111-1111-1111-1111-111111111111"
GIFT_ID = "22222222-2222-2222-2222-222222222222"
SHARE_ID = "33333333-3333-3333-3333-333333333333"
SUB_ID = "44444444-4444-4444-4444-444444444444"


@pytest.fixture
async def mixitup(aiohttp_server, srv):
    """A pretend MixItUp Developer API: 250 commands (so the list comes in pages); it records what it ran."""
    ran = []
    names = [{"ID": FOLLOW_ID, "Name": "TikTok follow", "Type": "Custom", "IsEnabled": True},
             {"ID": GIFT_ID, "Name": "TikTok gift", "Type": "Custom", "IsEnabled": True},
             {"ID": SHARE_ID, "Name": "Share shout", "Type": "Custom", "IsEnabled": False},
             {"ID": SUB_ID, "Name": "Sub hype", "Type": "Event", "IsEnabled": True}]
    names += [{"ID": f"00000000-0000-0000-0000-{i:012d}", "Name": f"cmd{i}", "Type": "Chat", "IsEnabled": True}
              for i in range(246)]

    async def listing(request):
        skip, size = int(request.query["skip"]), int(request.query["pageSize"])
        return web.json_response({"TotalCount": len(names), "Commands": names[skip:skip + size]})

    async def run(request):
        cid = request.match_info["id"]
        if cid not in {c["ID"] for c in names}:
            return web.json_response({"detail": f"Command with ID '{cid}' not found"}, status=404)
        ran.append((cid, await request.json()))
        return web.Response()

    app = web.Application()
    app.router.add_get("/api/v2/commands", listing)
    app.router.add_post("/api/v2/commands/{id}", run)
    server = await aiohttp_server(app)
    srv.S.data.update(mixitup_url=f"http://127.0.0.1:{server.port}",
                      tiktok_commands={"follow": FOLLOW_ID, "gift": GIFT_ID, "share": SHARE_ID, "sub": SUB_ID},
                      tiktok_command_gift_coins=100)
    server.ran = ran
    return server


async def settle(srv):
    await asyncio.sleep(0.05)
    if srv.mixit.tasks:
        await asyncio.gather(*srv.mixit.tasks)


async def test_follow_runs_its_command_once(client, srv, mixitup):
    who = {"user": "dancer", "display": "Dance Queen", "avatar": "https://example.com/a.jpg"}
    srv.tiktok.follow(who)
    srv.tiktok.follow(who)                      # follow / unfollow spam: no second command
    await settle(srv)
    assert len(mixitup.ran) == 1
    cid, body = mixitup.ran[0]
    assert cid == FOLLOW_ID and body["Arguments"] == "dancer"
    assert body["SpecialIdentifiers"] == {"tiktokevent": "follow", "tiktokuser": "dancer", "tiktokname": "Dance Queen",
                                          "tiktokavatar": "https://example.com/a.jpg"}
    assert srv.mixit.status()["last"]["ok"]


async def test_gifts_need_enough_coins_and_wait_for_the_combo(client, srv, mixitup):
    who = {"user": "fan", "display": "Fan", "avatar": ""}
    srv.tiktok.gift(who, "Rose", "", 1, count=5)                    # 5 coins: under the command's 100
    srv.tiktok.gift(who, "Doughnut", "", 30, count=2, streaking=True)  # mid-combo: wait for the end
    srv.tiktok.gift(who, "Doughnut", "", 30, count=4)               # the combo ends: 120 coins
    await settle(srv)
    assert len(mixitup.ran) == 1
    ids = mixitup.ran[0][1]["SpecialIdentifiers"]
    assert ids["tiktokgift"] == "Doughnut" and ids["tiktokgiftcount"] == "4" and ids["tiktokcoins"] == "120"


async def test_sub_and_share(client, srv, mixitup):
    who = {"user": "pal", "display": "Pal", "avatar": ""}
    srv.tiktok.subscribe(who, months=3)
    srv.tiktok.share(who)
    srv.tiktok.share(who)                       # once per person every few minutes
    await settle(srv)
    ran = dict(mixitup.ran)                     # they run side by side, in either order
    assert set(ran) == {SUB_ID, SHARE_ID} and ran[SUB_ID]["SpecialIdentifiers"]["tiktokmonths"] == "3"
    assert srv.tiktok.counts["share"] == 1


async def test_nothing_chosen_nothing_runs(client, srv, mixitup):
    srv.S.data["tiktok_commands"] = {}
    srv.tiktok.follow({"user": "x", "display": "X", "avatar": ""})
    await settle(srv)
    assert mixitup.ran == []


async def test_a_missing_command_is_reported(client, srv, mixitup):
    srv.S.data["tiktok_commands"] = {"follow": "99999999-9999-9999-9999-999999999999"}
    srv.tiktok.follow({"user": "x", "display": "X", "avatar": ""})
    await settle(srv)
    last = srv.mixit.status()["last"]
    assert not last["ok"] and "404" in last["detail"]


async def test_mixitup_offline_doesnt_stop_the_alert(client, srv, tv):
    srv.S.data.update(mixitup_url="http://127.0.0.1:9", tiktok_commands={"follow": FOLLOW_ID})
    srv.tiktok.follow({"user": "x", "display": "X", "avatar": ""})
    assert (await tv.next("follow"))["user"]["platform"] == "tiktok"
    await settle(srv)
    assert "Couldn't reach MixItUp" in srv.mixit.status()["last"]["detail"]


async def test_command_list_for_the_settings_page(client, srv, mixitup):
    r = await (await client.get("/api/mixitup/commands")).json()
    assert r["ok"] and len(r["commands"]) == 250                    # all pages
    assert {"id": SHARE_ID, "name": "Share shout", "type": "Custom", "group": "", "enabled": False} in r["commands"]
    srv.S.data["mixitup_url"] = ""
    r = await (await client.get("/api/mixitup/commands?fresh=1")).json()
    assert not r["ok"] and "address" in r["error"]


async def test_test_buttons_run_the_commands(client, srv, tv, mixitup):
    await client.post("/api/test/tiktok?kind=follow")
    r = await (await client.post("/api/test/tiktok?kind=share")).json()
    assert r == {"ok": True, "command": True}
    await client.post("/api/test/tiktok?kind=gift&size=big")
    await settle(srv)
    assert sorted(c for c, _ in mixitup.ran) == sorted([FOLLOW_ID, SHARE_ID, GIFT_ID])


async def test_settings_checks(client, srv):
    bad = [{"mixitup_url": "localhost:8911/api"}, {"tiktok_commands": {"follow": "not-an-id"}},
           {"tiktok_commands": ["x"]}]
    for body in bad:
        assert not (await (await client.post("/api/settings", json=body)).json())["ok"], body
    r = await (await client.post("/api/settings", json={"mixitup_url": "http://192.168.1.50:8912",
                                                        "tiktok_commands": {"follow": FOLLOW_ID, "raid": FOLLOW_ID, "gift": ""}})).json()
    assert r["ok"] and r["settings"]["tiktok_commands"] == {"follow": FOLLOW_ID}
    state = await (await client.get("/api/state")).json()
    assert state["status"]["mixitup"] == {"url_set": True, "last": None}
