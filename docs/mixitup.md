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
- Sub and resub `tier`: `1`, `2`, `3`, `prime`, or Twitch's `1000/2000/3000`.
- Hype train: `percent=` (0 to 100), or `progress=` and `goal=` as numbers.
  A higher `level` than last time shows a level-up banner. If no update
  arrives for 6 minutes, the bar hides by itself.
- `/welcome` shows straight away in the corner, even over another screen;
  everything else waits its turn in the queue.
