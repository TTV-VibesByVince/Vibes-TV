# MixItUp URLs

[← Back to the README](../README.md) · [All docs](README.md)

Add **one Web Request action (GET) per event**, pointing at Vibe TV. The
settings page lists these with copy buttons, already filled in with your
server's address.

| MixItUp event / command | URL |
| --- | --- |
| Shoutout command | `/shoutout/$targetusername` |
| Channel Raided | `/raid/$username?viewers=<raid viewer count>` |
| Followed | `/follow/$username` |
| Subscription Gifted | `/gift/$username?to=$targetusername` |
| Mass Subscriptions Gifted (optional) | `/giftbomb/$username?count=<amount>` |
| Subscribed | `/sub/$username?tier=<tier>` |
| Resubscribed | `/resub/$username?months=<months>&message=<message>` |
| Bits Cheered | `/bits/$username?amount=<bits>&message=<message>` |
| Watch Streak | `/streak/$username?count=<streak count>&message=<message>` |
| Modiversary | `/modiversary/$username?years=<years>` (or `&months=<months>`) |
| Gigantified Emote | `/gigantify/$username?emote=<emote ID or name>` |
| First chat message | `/welcome/$username` |
| Hype Train Start | `/hypetrain/start?level=<level>` |
| Hype Train progress / Level Up | `/hypetrain/progress?level=<level>&percent=<percent>` |
| Hype Train End | `/hypetrain/end?level=<level>` |
| A chat command | `/message?text=$allargs&from=$username` |
| | `/logo`: clear the queue and the hype bar, back to the logo |
| | `/reload`: reload every TV page |
| | `/status`: JSON status |

Words in `<angle brackets>` are MixItUp's special identifiers for that
event; pick the matching ones in MixItUp's event editor (the names vary by
event and version). Everything after `?` is optional except the bits
`amount`:

- Shoutout and raid: `&clip=0|1`, `&sound=0|1`, `&display=Name`,
  `&game=Game`, `&avatar=<picture link>`.
- Sub and resub `tier`: `1`, `2`, `3`, `prime`, `Tier 2`, or Twitch's
  `1000/2000/3000`. **Tier 2** gets a bigger card (two stars, confetti
  cannons, a short shake) and **Tier 3** the biggest (spotlights, a gold
  crown, coins raining). If MixItUp has no tier variable for your event, use
  separate URLs instead: `/sub/$username/tier2` and `/sub/$username/tier3`,
  picked with a condition in MixItUp.
- Hype train: `percent=` (0 to 100), or `progress=` and `goal=` as numbers.
  A higher `level` than last time shows a level-up banner. If no update
  arrives for 6 minutes, the bar hides by itself.
- Modiversary: `years=` or `months=` (18 months shows as "18 MONTHS", 24 as
  "2 YEARS"). It uses Twitch's mod green unless you pick another colour.
- Gigantified emote `emote=`: an **emote ID** (like `emotesv2_…` or `25`) or
  an **image link** always works, for any emote. An emote **name** (like
  `LUL`) is looked up on Twitch: global emotes, and your own channel's if you
  enter your channel under **Settings > Twitch API**. Anything it can't find
  is shown as big text. Emote images are small (112 pixels at most, older
  ones less), so a giant emote is a little soft.
- `/welcome` shows straight away in the corner, even over another screen;
  everything else waits its turn in the queue.

## Check what MixItUp sends

**Settings > Last requests received** lists the last 30 event URLs exactly
as they arrived. If a variable didn't exist for that event, you'll see it
empty (`tier=`) or left as text (`$usersubplan`): pick a different
identifier in MixItUp's event editor.

## What the tiers look like

| Tier 2 | Tier 3 |
| --- | --- |
| ![Tier 2 sub: TIER 2 in silver, two stars and confetti cannons](screenshots/sub-tier2.jpg) | ![Tier 3 sub: spotlights, a gold crown and gold coins](screenshots/sub-tier3.jpg) |

Tier 1 and Prime subs keep the regular sub card.
