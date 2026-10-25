# Changelog

What changed in each version of Vibe TV. The version is shown at the top of
the settings page. MixItUp URLs that worked in an earlier version keep
working in later ones.

## 1.7 (2026-10-25)

- **Alert sizes on the stream overlay**: for each alert type, **Compact** (a
  card in your corner), **Centre** (a bigger card in the middle) or **Full
  screen** (the TV's own animation over your game). Raids are full screen
  by default. Behind big alerts the stream is darkened, with a setting for
  how much.
- **Fix**: the TV's "play a clip after shoutouts and raids" switch also
  turned clips off on the overlay. Each screen now has its own switch,
  clearly named. `&clip=0` still skips clips everywhere; `&clip=1` forces
  one on the TV.

## 1.6 (2026-10-25)

- **Text to speech** (optional, off by default): TikTok LIVE chat, and
  anything MixItUp sends to `/tts`, read aloud in a Microsoft Edge voice
  (edge-tts: free, no key). One message at a time from its own queue, on
  the stream overlay by default, with a "now reading" bubble. Voice picker
  with preview, speed, volume and what it says. Against trolls: commands and
  links are skipped, a per-person cooldown, a length limit and a
  blocked-words list. `/tts/skip` stops it.
- **Giant emotes from MixItUp**: `/gigantify/$username?emote=$emoteurl&name=$emotename`.
  Twitch emote links are switched to the biggest, animated size, and the
  name goes in the caption.
- **Unfilled MixItUp variables are ignored** instead of shown on screen (no
  more a giant `<EMOTE ID OR NAME>`). **Last requests received** says which
  ones arrived unfilled.
- The settings page's MixItUp URLs (and the docs) use MixItUp's real
  variable names for every event, so the copy buttons give working URLs.
- Pillow 13 and aiohttp 3.14.

## 1.5 (2026-10-22)

- **Stream overlay** (`/overlay`): the same alerts on your stream, as an
  OBS Browser Source. Fully transparent, nothing on screen between alerts,
  and each alert a compact, see-through card in the corner you pick, with
  the same words, colours, themes and pictures as the TV. Welcome pop-ups
  and the hype train bar work there too. Settings for position, size,
  panel opacity and how long each alert stays up (6 seconds by default).
- **Two queues**: the TV and the overlay each have their own, so an overlay
  alert never waits for a clip on the TV. Room lights follow the TV only.
- **Choose where each alert plays**: TV, overlay or both, per alert type
  (everything on both by default, except gigantified emotes: TV only). Any
  alert URL can override it with `&screen=tv|overlay|both`; `/logo` clears
  both screens, or one with `?screen=`.
- **No clips on the overlay by default**, so a clip's sound doesn't play
  twice. It can be switched on.
- **TikTok LIVE** (optional, off by default): follows, subscriptions and
  gifts from your TikTok live as Vibe TV alerts, through the unofficial
  open source TikTokLive library. Gift combos show once, with the total;
  small gifts can be skipped. A new TikTok gift card on the TV and overlay.
- Settings page: a TV / Stream overlay switch on the live preview (the
  overlay over a stand-in game scene), a **Send tests to** picker for the
  test buttons, a **Stream overlay** section with the OBS address and tips,
  and a **TikTok LIVE** section with status and test buttons.
- Existing settings files and backups load as before; the new settings
  start at their defaults. MixItUp URLs are unchanged.

## 1.4 (2026-10-17)

- **Bigger subs for bigger tiers**: Tier 2 subs and resubs get two stars,
  confetti cannons and a short shake; Tier 3 gets spotlights, a gold crown,
  a slamming "TIER 3" and gold coins raining. Optional light URLs per tier.
  The tier can also be part of the URL: `/sub/<user>/tier3`.
- **Watch streak** (`/streak`): a fuse of dots lights up, the streak counts
  up, and a bed of fire burns along the bottom.
- **Modiversary** (`/modiversary`): a sword slash across the screen, then
  two swords cross behind a shield with their picture, in mod green.
- **Gigantified emotes** (`/gigantify`): the emote bursts onto the TV, huge
  and wobbling (animated emotes play animated). Works with an emote ID, an
  image link, or a name (looked up on Twitch).
- **Last requests received** on the settings page: the exact URLs MixItUp
  sent, to check its variables came through.
- **GO FOLLOW** on the shoutout card is twice as big.
- Settings: your Twitch channel (for finding emotes by name), timings and
  text for the new screens, test buttons for all of them.

## 1.3.1 (2026-10-17)

- **Icon**: Vibe TV has an icon, used for the browser tab on the TV and
  settings pages and in the settings page header.
- **Ready-built image**: GitHub builds the image and publishes it as
  `ghcr.io/ttv-vibesbyvince/vibes-tv` for Intel/AMD and ARM, and rebuilds it
  every week with the newest yt-dlp. No more building it yourself: updating
  is a re-pull.
- **Tests**: an automated test suite runs on every change.
- **Fix**: uploaded logo names that a browser sends percent-encoded
  (`my%20logo.png`) are now decoded instead of mangled.
- Docs reorganised: the README is an overview; the how-tos live in `docs/`.

## 1.3 (2026-10-16)

- **New screens**: subs (`/sub`), resubs with the month count and their
  message (`/resub`), bits with gems raining in Twitch's cheer colours
  (`/bits`).
- **First-time chatters** (`/welcome`): a small pop-up in the corner that
  doesn't wait in the queue or interrupt anything.
- **Hype train** (`/hypetrain/start|progress|end`): a progress bar along the
  bottom, with banners when it starts, levels up and ends.
- **Editable text**: every line on every screen, with `{placeholders}` and
  `[optional parts]`.
- **Colours per event**: the avatar's, the theme's, or one you pick. Lights
  follow it.
- **Themes**: Halloween (bats), Winter holidays (snowflakes), Valentine's,
  St Patrick's (clovers). One-click switch and a yearly date schedule.
- **Backup and restore** of all settings in one file.
- **Fonts are bundled**, so the TV page no longer needs Google Fonts.
- Change: when a profile picture has no usable colour, the theme colour is
  used (for the screen and the lights) instead of leaving the lights alone.

## 1.2 (2026-10-15)

- **Follows** (`/follow`) and **gifted subs** (`/gift`, `/giftbomb`).
  Gift events from the same person arriving together become one screen.
- **Lite mode** for TV sticks and smart TVs, chosen automatically.
- **Fix**: a white flash before clips on Android TV browsers. Clips now
  buffer while the card is on screen and only appear once playing.

## 1.1 (2026-10-15)

- **Settings page** (`/admin`): live preview, test buttons, logo library
  with uploads, timings, Twitch keys, light URLs, and the MixItUp URLs to
  copy. Optional password.
- **New raid animation**.
- Cards show straight away and the clip downloads in the background.
- Names keep their capitals without Twitch keys; a big initial replaces a
  missing picture.

## 1.0

- The first version: a looping logo, shoutout and raid cards, messages,
  Twitch clips and light colour URLs, triggered by MixItUp.
