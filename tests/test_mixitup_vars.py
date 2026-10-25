"""1.6: MixItUp variables that arrive unfilled are ignored instead of shown,
and gigantified emotes take MixItUp's $emoteurl and $emotename."""


async def test_placeholder_emote_is_not_shown(client, tv, srv):
    r = await client.get("/gigantify/Fan?emote=<emote ID or name>")
    assert r.status == 400                                     # nothing usable: skipped, not "<EMOTE ID OR NAME>"
    assert await tv.next("gigantify", timeout=1) is None
    entry = srv.tv.requests[0]
    assert "emote" in entry["note"] and "not filled in" in entry["note"]
    r = await client.get("/gigantify/Fan?emote=$emoteurl&name=$emotename")
    assert r.status == 400


async def test_emoteurl_and_emotename(client, tv):
    link = "https://static-cdn.jtvnw.net/emoticons/v2/emotesv2_0123456789abcdef/static/light/1.0"
    await client.get(f"/gigantify/Fan?emote={link}&name=VibeHype")
    card = await tv.next("gigantify")
    assert card["emote"]["url"].endswith("/emotesv2_0123456789abcdef/default/dark/3.0")   # biggest, animated
    assert card["emote"]["name"] == "VibeHype" and card["text"]["caption"] == "Fan gigantified VibeHype"


async def test_other_image_links_are_kept(client, tv):
    await client.get("/gigantify/Fan?emote=https://cdn.example.com/my-emote.png")
    assert (await tv.next("gigantify"))["emote"]["url"] == "https://cdn.example.com/my-emote.png"


async def test_unfilled_message_is_dropped_but_alert_plays(client, tv, srv):
    r = await client.get("/resub/Loyal?months=$usersubmonths&tier=<tier>&message=<their message>")
    assert r.status == 200
    card = await tv.next("resub")
    assert card["text"]["message"] == "" and card["tier_level"] == 1
    assert "months, tier, message" in srv.tv.requests[0]["note"]


async def test_mixitup_sub_plan_names(client, tv):
    for plan, level in (("Tier 3", 3), ("Prime", 1), ("Tier 2", 2)):
        await client.get(f"/sub/Fan?tier={plan}")
        assert (await tv.next("sub"))["tier_level"] == level
