# Roadmap

Ideas for Vibe TV, roughly in the order they're likely to happen. Nothing
here is promised; [open an issue](https://github.com/TTV-VibesByVince/Vibes-TV/issues/new/choose)
to vote for one or suggest your own.

## Next

- **Event history with a Replay button** on the settings page, for the raid
  you missed while talking.
- **Queue view**: see what's waiting, skip one, or clear them all.
- **A light effect per event**: follows breathe, gifts rainbow, raids
  strobe, instead of only a colour.
- **Sounds**: upload a sound for each event type.

## Later

- **Connect to Twitch directly** (EventSub), so follows, subs, bits, raids
  and hype trains arrive without a bot, with exact gift recipient lists.
- **Scenes**: several logos on rotation, and `starting soon`, `be right
  back` and `ending` screens switched by URL.
- **Channel point redemptions**: a picture or video per reward.
- **Clip improvements**: don't repeat a streamer's last clip, prefer recent
  ones, and a `!clip <link>` command for chat.

## Maybe

- Fully Kiosk remote control: turn the TV screen on when you go live and off
  when you end.
- A notification when a TV disconnects.
- Each TV's frame rate on the settings page, to show when lite mode helps.
- A VIP raid card for friends, with their own intro video.

## Done

- **Transparent overlay mode** (1.5): the same alerts as an OBS Browser
  Source at `/overlay`, with its own queue and a TV / overlay / both choice
  per alert type. See [Stream overlay](docs/overlay.md).
- **TikTok LIVE alerts** (1.5): follows, subscriptions and gifts, optional.
  See [TikTok LIVE](docs/tiktok.md).
- **Text to speech** (1.6): TikTok chat and `/tts` read aloud with Edge
  voices. See [Text to speech](docs/tts.md).
