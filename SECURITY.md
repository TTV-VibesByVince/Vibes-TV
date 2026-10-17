# Security

## What Vibe TV is designed for

Vibe TV runs on your **home network**. Keep it behind your router: don't
forward port 8777 or put it on the internet.

- **The event URLs and the TV page are open on purpose**, so MixItUp and the
  TV can use them without logging in. Anyone who can reach them can make
  screens appear.
- **The settings page** (`/admin` and `/api/...`) can have a password: set
  `ADMIN_PASSWORD` on the container. It uses your browser's standard login
  box over plain HTTP, which is fine on a home network but not across the
  internet.
- **Twitch API keys** are stored in `config/settings.json` on your server.
  The settings page never sends the client secret back to the browser, and
  backups leave it out unless you tick the box.
- **Lights**: Vibe TV only calls the light URLs you enter.

## Reporting a problem

Please **don't open a public issue** for a security problem. Report it
privately instead: on this repository's **Security** tab, click **Report a
vulnerability**. Include the version (top of the settings page) and how to
reproduce it.

Fixes go into the latest version; please update to it first.
