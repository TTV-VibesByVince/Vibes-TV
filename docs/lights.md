# Lights

[← Back to the README](../README.md) · [All docs](README.md)

Vibe TV calls your lights itself: **don't** add light URLs to MixItUp.

1. When a card starts, it picks the strongest colour from the person's
   profile picture and calls the **Card colour URL** with `{hex}` replaced
   by it (e.g. `ff7800`).
2. The lights stay that colour through the card and the clip.
3. When the TV goes back to the logo, it calls the **Back-to-normal URL**.

The **Raid URL** (optional) is used instead of the card colour for raids,
e.g. a sparkle effect in the raider's colour.

## With Govee Lights Controller

[Govee Lights Controller](https://github.com/TTV-VibesByVince/Govee-Lights-Controller)
is our companion Windows app for Govee lights. Using V1.3 or newer, on the
PC running it turn on **Settings > Accept requests from my network**, save
and restart it. Then use the **PC's** address (not the server's):

- Card colour URL: `http://<pc-ip>:8765/color/{hex}`
- Raid URL: `http://<pc-ip>:8765/sparkle/{hex}/12`
- Back-to-normal URL: `http://<pc-ip>:8765/default`

The Test buttons always send purple (`9146ff`); real events use the avatar
colour. Give the PC a fixed address (a DHCP reservation in your router) so
the URLs keep working.
