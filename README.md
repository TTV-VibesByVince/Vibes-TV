# Vibe TV

A stream TV for the wall behind you. It loops your logo, and when
[MixItUp](https://mixitupapp.com) sends a web request it shows a shoutout,
raid, follow or gifted-sub screen. It can then play one of that streamer's
Twitch clips, and set your room lights to the colour of their profile picture.

It runs in Docker (a NAS is ideal). The TV just opens a web page, and
everything is set up from a settings page in the browser.

## Features

- **Shoutouts**: avatar, name, last game and a `twitch.tv/` link, then a
  random clip from their most-viewed clips.
- **Raids**: a full-screen animation with hazard tape, a slamming RAID! title,
  a portal around the raider's avatar, warp streaks, one glowing dot per
  raider flying in, and a count-up. Then a clip.
- **Follows**: "Thanks for the follow!" with their picture and floating hearts.
- **Gifted subs**: the gifter, then every recipient's picture and name.
  One-at-a-time gift events from MixItUp are combined into one screen.
- **Messages**: a big text bubble for chat commands.
- **Logo library**: upload videos or images, pick which one loops.
- **Light sync**: calls your light controller with the avatar's colour,
  e.g. the Govee Light Controller V1.3+, or anything that takes a colour in
  a URL.
- **Lite mode** for TV sticks and smart-TV browsers (Fully Kiosk etc.).
- A live preview and test buttons for every event on the settings page.
- Events queue up and play one after another.

## Install

You need a machine that runs Docker all the time (a NAS, a mini PC, a
Raspberry Pi 4/5) on the same network as the TV and the PC running MixItUp.

### Portainer

1. Download this repository as a ZIP (green **Code** button > Download ZIP),
   unzip it, and make a `.tar` of the build files. In PowerShell, inside the
   unzipped folder, run:
   `tar -cf vibe-tv.tar Dockerfile requirements.txt app`
2. **Images > Build a new image**: name `vibe-tv:latest`, method **Upload**,
   select `vibe-tv.tar`, then **Build the image**.
3. **Stacks > Add stack**, name `vibe-tv`, **Web editor**, paste this, and
   change the folder paths on the left to a folder on your server:

   ```yaml
   services:
     vibe-tv:
       image: vibe-tv:latest
       container_name: vibe-tv
       restart: unless-stopped
       ports:
         - "8777:8777"
       environment:
         - TZ=Etc/UTC
         - ADMIN_PASSWORD=
       volumes:
         - /volume1/docker/vibe-tv/media:/media
         - /volume1/docker/vibe-tv/config:/config
         - /volume1/docker/vibe-tv/cache:/cache
   ```

4. **Deploy the stack**.

### Synology Container Manager (or plain Docker Compose)

1. Copy this folder to the server, e.g. `/volume1/docker/vibe-tv`.
2. Container Manager > **Project** > **Create**, choose that folder; it finds
   `docker-compose.yml`. Anywhere else: `docker compose up -d --build`.

### Then

1. Open `http://<server-ip>:8777/admin` and upload your logo.
2. On the TV, open `http://<server-ip>:8777/tv` full screen.
3. If the server has a firewall, allow TCP 8777 from your home network.

## MixItUp

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
| A chat command | `/message?text=$allargs&from=$username` |
| | `/logo`: clear the queue and go back to the logo |
| | `/reload`: reload every TV page |
| | `/status`: JSON status |

Check the exact variable names (raid viewer count, gift amount) in
MixItUp's event editor. Shoutout and raid also take `&clip=0|1`,
`&sound=0|1`, `&display=Name`, `&game=Game` and `&avatar=<picture link>`.

## Twitch API keys (optional, recommended)

These add real display names, avatars, last game and clips. Without them,
cards show the name as typed and an initial instead of a picture (unless
MixItUp sends `&avatar=`).

1. [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps) >
   **Register Your Application**. OAuth Redirect URL: `http://localhost`,
   Category: Other, Client type: Confidential.
2. Copy the **Client ID**, click **New Secret**, copy that too.
3. Paste both into the settings page > Twitch API, **Save**, then
   **Test connection**.

## Lights

Vibe TV calls your lights itself: **don't** add light URLs to MixItUp.

1. When a card starts, it picks the strongest colour from the person's
   profile picture and calls the **Card colour URL** with `{hex}` replaced
   by it (e.g. `ff7800`).
2. The lights stay that colour through the card and the clip.
3. When the TV goes back to the logo, it calls the **Back-to-normal URL**.

The **Raid URL** (optional) is used instead of the card colour for raids,
e.g. a sparkle effect in the raider's colour.

For the Govee Light Controller (V1.3+), on the PC running it turn on
**Settings > Accept requests from my network**, save and restart it. Then
use the **PC's** address (not the server's):

- Card colour URL: `http://<pc-ip>:8765/color/{hex}`
- Raid URL: `http://<pc-ip>:8765/sparkle/{hex}/12`
- Back-to-normal URL: `http://<pc-ip>:8765/default`

The Test buttons always send purple (`9146ff`); real events use the avatar
colour. Give the PC a fixed address (a DHCP reservation in your router) so
the URLs keep working.

## Slow TVs

Settings > Timing > **TV animation quality**. *Auto* (the default) uses lite
mode on TV sticks, smart TVs and Android boxes such as Fully Kiosk Browser,
and full mode on a PC. Lite keeps the same animations but drops what weak
graphics chips struggle with (blurring the playing logo, soft glows,
animated filters) and draws particles at half resolution. Force it for one
TV with `/tv?mode=lite` or `/tv?mode=full`.

## Settings page password

Set `ADMIN_PASSWORD` to protect `/admin` (the browser asks for a user name
and password; the user name can be anything). The TV page and the MixItUp
URLs stay open on your network.

## Updating

Rebuild the image from the new files (Portainer: **Images > Build** with the
same name, then **Containers > vibe-tv > Recreate**). Your logos and
settings live in the `media` and `config` folders and are kept. Rebuilding
also updates yt-dlp, which fixes most "clips stopped working" problems.

## License

[MIT](LICENSE)
