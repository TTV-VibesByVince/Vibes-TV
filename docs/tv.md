# The TV

[← Back to the README](../README.md) · [All docs](README.md)

## Fully Kiosk Browser

The TV page is an ordinary web page, so any modern browser shown full
screen works. We use **[Fully Kiosk Browser](https://www.fully-kiosk.com)**
on an Android-based TV. It's built for screens that stay on all day: it
opens one page full screen, keeps it there, survives restarts, and plays
video without anyone touching a remote. It runs on Android TV, Google TV,
Fire TV sticks and Android boxes (Google Play or the Amazon Appstore). The
free version is enough for Vibe TV.

Setup (menu names can differ a little between versions):

1. Install Fully Kiosk Browser on the TV and open it.
2. **Start URL**: `http://<server-ip>:8777/tv`
3. **Web Content Settings > Autoplay Videos**: on. Needed for the logo
   loop and clips, and for clip sound if you turn sound on.
4. **Device Management > Keep Screen On**: on.
5. **Device Management > Launch on Boot**: on, so the TV comes back to
   Vibe TV after a power cut or restart.
6. Hide the status and navigation bars (full screen) under
   **Toolbars & Appearance**.

Tips:

- TV-stick graphics chips are much weaker than a PC's. Vibe TV detects
  Fully Kiosk and other TV browsers and switches to **lite mode**
  automatically (see [Slow TVs](#slow-tvs)).
- A small red dot in the bottom-right corner means the TV has lost its
  connection to the server. It reconnects by itself.
- Changed something? **Reload TVs** on the settings page refreshes every TV
  without touching the remote.

Other options: Chrome or Edge on a PC or mini PC (press F11), or Chromium on
a Raspberry Pi started with `--kiosk http://<server-ip>:8777/tv`. Built-in
smart-TV browsers and Amazon Silk work too, but often won't autoplay video
or stay full screen.

## Slow TVs

Settings > Timing > **TV animation quality**. *Auto* (the default) uses lite
mode on TV sticks, smart TVs and Android boxes such as Fully Kiosk Browser,
and full mode on a PC. Lite keeps the same animations but drops what weak
graphics chips struggle with (blurring the playing logo, soft glows,
animated filters) and draws particles at half resolution. Force it for one
TV with `/tv?mode=lite` or `/tv?mode=full`.
