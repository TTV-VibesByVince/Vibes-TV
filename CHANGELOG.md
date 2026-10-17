# Changelog

What changed in each version of Vibe TV. The version is shown at the top of
the settings page. MixItUp URLs that worked in an earlier version keep
working in later ones.

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
