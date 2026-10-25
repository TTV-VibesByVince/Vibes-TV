# Text to speech

[← Back to the README](../README.md) · [All docs](README.md)

Vibe TV can read **TikTok LIVE chat** aloud, and anything MixItUp sends to
`/tts` (a chat command, a channel-points reward), in a natural Microsoft
Edge voice. It's off until you switch it on.

## How it works (and its limits)

Vibe TV uses [edge-tts](https://github.com/rany2/edge-tts), a well-known
open source Python library that uses the same online voices as Microsoft
Edge's **Read aloud**: hundreds of neural voices in dozens of languages,
free, no account or key. It's **unofficial**, so Microsoft could change or
limit it. The server needs internet access to make each line.

The server turns each message into a short audio file and sends it to the
**stream overlay** (by default), which plays it. Messages are read **one at
a time**, from their own short queue, so they never hold up alerts.

## Switch it on

Settings > **Text to speech**:

1. Turn on **Text to speech on**.
2. Leave **Read TikTok LIVE chat** on, and make sure **TikTok LIVE** is set up
   ([TikTok LIVE](tiktok.md)).
3. Pick a **Language** and a **Voice**, and press **Preview** to hear it on
   the settings page.
4. Save.

In OBS, tick **Control audio via OBS** on the overlay's Browser Source, so
the voice shows up in your audio mixer and goes out on stream. Without it,
OBS still plays it on your PC, but your viewers won't hear it.

## Settings

| Setting | What it does |
| --- | --- |
| Speed | -50 (slower) to 100 (twice as fast), in percent. |
| Volume | 0 to 1, on the overlay (or TV). |
| What it says | `{name} says {message}` by default. Must include `{message}`. `[{name}: ]{message}` reads the name only when there is one. |
| Longest message | Longer messages are cut at a word, 150 characters by default. |
| Same person again after | A cooldown per person, 15 seconds by default, so one viewer can't hog it. |
| Never read messages with these words | Whole words, comma or one per line. A message with any of them isn't read at all. |
| Show what's being read on screen | A small bubble with their name and message, in the corner opposite your alerts. |

Always skipped: chat commands (starting with `!`) and messages with links.
When chat is busy, only the newest 5 messages wait their turn, and a message
that has waited a minute is dropped, so it never falls far behind.

## Where it plays

On the **stream overlay** by default. **Settings > Stream overlay > Where
each alert plays > Text to speech** can move it to the TV, or both. One
request can override it with `&screen=tv|overlay|both`.

## From MixItUp

| What | URL |
| --- | --- |
| Read a chat command's text | `/tts?text=$allargs&from=$username` |
| Stop what's being read | `/tts/skip` |

For example, a `!tts` command in MixItUp with a Web Request action to
`http://<server-ip>:8777/tts?text=$allargs&from=$username` reads Twitch chat
the same way, with the same filters and cooldown. `/tts/skip` on a Stream
Deck button stops a message you don't want read. `/logo` also stops it and
clears what's waiting.

## Test it

Under Settings > Text to speech, type a line and press **Read aloud**
(after saving). It plays where text to speech is routed, so open the
overlay or watch the live preview. **Skip** stops it. The status line shows
how many were read and skipped, and the last problem if making a voice
failed.

## Troubleshooting

- **Nothing heard on stream**: tick **Control audio via OBS** on the Browser
  Source and check its fader in the audio mixer. The settings page's live
  preview is always silent, so you don't hear everything twice.
- **"Last problem: …" on the settings page**: the server couldn't reach
  Microsoft's voice service. Check the server's internet connection; it
  tries again with the next message.
- **On a TV browser**: Fully Kiosk Browser needs **Autoplay Videos** on (it
  covers audio too).

## License

edge-tts is © rany2 and contributors, under the LGPL-3.0. Vibe TV doesn't
include its code; the library is installed into the image from PyPI.
