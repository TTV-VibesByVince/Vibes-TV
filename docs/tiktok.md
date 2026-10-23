# TikTok LIVE

[← Back to the README](../README.md) · [All docs](README.md)

If you also go live on TikTok, Vibe TV can show your TikTok **follows**,
**subscriptions** and **gifts** with the same cards, on the TV and the
stream overlay. It's optional and off until you switch it on.

## How it works (and its limits)

TikTok has no public API for live events, so Vibe TV uses
[TikTokLive](https://github.com/isaackogan/TikTokLive), a well-known open
source Python library that reads the same live feed the TikTok app shows
viewers. It's **unofficial**: TikTok doesn't support it, and when TikTok
changes something it can stop working until the library is updated (pulling
the latest Vibe TV image picks up the newest compatible version).

TikTokLive's servers (eulerstream.com) sign the connection requests. That
works without an account at a low rate; if connecting fails often, a free
or paid key from eulerstream.com can help (see below).

## Switch it on

Settings > **TikTok LIVE**:

1. Turn on **Listen to my TikTok LIVE**.
2. Enter **your TikTok username** (with or without the `@`).
3. Save.

Vibe TV then checks every minute whether you're live, and connects when you
are. The chip next to the section title says what it's doing: waiting for
you to go live, connected (with a count of this session's follows, subs and
gifts), or the problem if something is wrong. It reconnects by itself.

You can also set these on the container instead: `TIKTOK_ENABLED=1`,
`TIKTOK_USERNAME=yourname` and, optionally, `TIKTOK_SIGN_KEY`.

## What shows

| TikTok event | Card |
| --- | --- |
| Follow | The follow card, with a small **TIKTOK** tag. Someone who unfollows and follows again within an hour is only shown once. |
| Subscription | The sub card (or resub, with the month count), with the **TIKTOK** tag. |
| Gift | A **TikTok gift** card: the gift's picture, its name, how many and the coin total, with gems raining in colours by value. |

**Combos**: tapping the same gift again and again (a "streak") sends one
event per tap. Vibe TV waits for the combo to end and shows it **once**, with
the total ("5× Rose!").

**Smallest gift shown**: gifts worth fewer coins than this (the combo
total) are skipped, so a stream of Roses doesn't flood the queue. Default 1
(everything shows).

The TikTok gift card has its own text, colour and routing on the settings
page (**Text & colours** and **Stream overlay > Where each alert plays**).
Follows and subscriptions use the follow and sub settings.

## Test it

The **Follow**, **Subscription**, **Small gift** and **Big gift** buttons
under Settings > TikTok LIVE play made-up TikTok alerts. They don't need a
TikTok connection, and they follow **Send tests to**.

## Signing key (optional)

Settings > TikTok LIVE > **Signing key**: a key from
[eulerstream.com](https://www.eulerstream.com) raises the signing limits.
It's stored like the Twitch secret: never shown again on the page, and left
out of backups unless you tick **Include the secrets**. Leave the box empty
to keep it, or type `-` to remove it.

## Troubleshooting

- **"isn't live" while you are**: TikTok can take a minute to report a new
  live. Wait for the next check, or check the username.
- **A problem about signing or rate limits**: wait a few minutes, or add a
  signing key.
- **"The TikTokLive library isn't installed"**: you're running an image
  built before 1.5, or a custom one. Pull the latest image.

## License

TikTokLive is © Isaac Kogan and contributors, under the AGPL-3.0 with an
added permission that allows using it in overlays and bots like Vibe TV.
Vibe TV doesn't include its code; the library is installed into the image
from PyPI.
