# Install and update

Vibe TV runs as one Docker container. The TV only opens a web page, and everything else is set up in the browser.

[← Back to the README](../README.md) · [All docs](README.md)

## Pick your setup

You need a machine that runs Docker all the time (a NAS, a mini PC, a
Raspberry Pi 4/5) on the same network as the TV and the PC running MixItUp.

The image is built by GitHub on every update and published as
**`ghcr.io/ttv-vibesbyvince/vibes-tv:latest`** (Intel/AMD and ARM), so
there's nothing to build yourself.

### Portainer

1. **Stacks > Add stack**, name `vibe-tv`, **Web editor**, paste this, and
   change the folder paths on the left to a folder on your server and `TZ`
   to your timezone:

   ```yaml
   services:
     vibe-tv:
       image: ghcr.io/ttv-vibesbyvince/vibes-tv:latest
       container_name: vibe-tv
       restart: unless-stopped
       ports:
         - "8777:8777"
       environment:
         - TZ=America/New_York
         - ADMIN_PASSWORD=
       volumes:
         - /volume1/docker/vibe-tv/media:/media
         - /volume1/docker/vibe-tv/config:/config
         - /volume1/docker/vibe-tv/cache:/cache
   ```

2. **Deploy the stack**.

### Synology Container Manager, or plain Docker Compose

1. Make a folder on the server, e.g. `/volume1/docker/vibe-tv`, and put
   this repository's `docker-compose.yml` in it.
2. Container Manager > **Project** > **Create**, choose that folder; it finds
   `docker-compose.yml`. Anywhere else: `docker compose up -d`.

To build the image yourself instead (e.g. after changing the code), put the
whole repository in that folder and replace the `image:` line with
`build: .`.

### Then

1. Open `http://<server-ip>:8777/admin` and upload your logo.
2. On the TV, open `http://<server-ip>:8777/tv` full screen (see
   [The TV](tv.md) below).
3. If the server has a firewall, allow TCP 8777 from your home network.

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

## Connect your Twitch account (optional)

The keys above only let Vibe TV look up public things. Connecting your
account lets it hear your channel's events straight from Twitch, for the
[end credits](credits.md#with-twitch-connected): mods and VIPs who chat are
added by themselves, and a new list starts when you go live.

1. Settings > **Setup** > Twitch API > **Connect Twitch** (the keys must be
   saved first).
2. On your phone or PC, open the **twitch.tv/activate** link shown, type the
   code, and approve what Vibe TV asks for: reading chat, followers, bits,
   the hype train and shoutouts.
3. The settings page shows **Connected as @you** by itself.

### Alerts straight from Twitch

Once connected, each alert can play straight from Twitch instead of from
MixItUp's request: Settings > Setup > **Alerts from Twitch**, tick the ones
you want (or **Tick all**), and save.

| Alert | From Twitch |
| --- | --- |
| Follows | Yes |
| Subs and resubs | Yes, with the tier, months and their message |
| Gifted subs | Yes, and a gift bomb is one screen with exactly who got them |
| Bits | Yes, with their message |
| Raids | Yes, with the raider's picture and viewer count |
| Watch streaks | Yes, with their message |
| Modiversaries | Yes |
| Gigantified emotes | Yes |
| Hype train | Yes: start, progress, level up and end, with the exact progress |
| Shoutouts | When you or a mod use Twitch's own `/shoutout` |
| First-time chatters | No: Twitch doesn't say who's new, so these stay with MixItUp's `/welcome` |

For a ticked alert, MixItUp's request is **ignored while Twitch is
connected**, so it can't play twice even if you leave it in MixItUp
(**Last requests received** says so). If the connection drops, MixItUp's
requests play again until it's back. The settings page's test buttons
always play. Lights, routing, sizes, text and colours all work the same
whichever way an alert arrives.

Your server connects out to Twitch, like a browser does: nothing has to be
opened on your router. The login is kept in `config/twitch_login.json`, never
in your settings or backups, and renews itself; if Vibe TV isn't running for
30 days in a row, press Connect again. **Disconnect** forgets it.

## Settings page password

Set `ADMIN_PASSWORD` to protect `/admin` (the browser asks for a user name
and password; the user name can be anything). The TV page and the MixItUp
URLs stay open on your network.

## Updating

Pull the latest image and recreate the container. Your logos and settings
live in the `media` and `config` folders and are kept.

- **Portainer**: **Stacks > vibe-tv > Editor**, click **Update the stack**,
  turn on **Re-pull image and redeploy**, and confirm. (Or **Containers >
  vibe-tv > Recreate** with **Re-pull image** on.)
- **Container Manager**: pull the image again (it offers an **Update** on
  the image when a newer one exists), then restart the project. Menu names
  vary a little between DSM versions.
- **Docker Compose**: `docker compose pull && docker compose up -d`.

The image is also rebuilt every Monday with the newest yt-dlp, so updating
fixes most "clips stopped working" problems even when nothing else changed.
Then click **Reload TVs** on the settings page.

Pinning a version instead of `latest` (e.g. `:1.3`) keeps you on it until
you change the tag.
