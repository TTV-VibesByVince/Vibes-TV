# Contributing

Thanks for wanting to help. Bug reports and ideas are just as useful as
code: use the [issue forms](https://github.com/TTV-VibesByVince/Vibes-TV/issues/new/choose).

## How it's put together

| Path | What it is |
| --- | --- |
| `app/server.py` | The whole server (aiohttp): MixItUp URLs, the event queue, Twitch lookups, clips, lights, settings, the settings page's API |
| `app/static/index.html` | The TV page: every screen and animation (HTML, CSS and plain JavaScript, no build step) |
| `app/static/admin.html` | The settings page |
| `app/static/fonts/`, `app/static/icon/` | Bundled fonts and the icon |
| `tests/` | The test suite (pytest) |
| `docs/` | Guides, screenshots, the demo video and the brand files |

## Run it locally

You need Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export MEDIA_DIR=./media CACHE_DIR=./cache CONFIG_DIR=./config   # Windows: set MEDIA_DIR=media (etc.)
python app/server.py
```

Then open <http://localhost:8777/admin> and <http://localhost:8777/tv>. The
settings page's test buttons fire every event, so you don't need MixItUp.

Or with Docker: replace the `image:` line in `docker-compose.yml` with
`build: .` and run `docker compose up --build`.

## Run the tests

```bash
pytest -q
```

They run in a few seconds and also run on GitHub for every push and pull
request.

## Ground rules

- **Never change what an existing URL does.** People have these in their
  MixItUp commands. New URLs and new optional `?options` are fine.
- **New behaviour is opt-in** when it changes what an existing setup shows.
- **Keep the TV page light.** It has to run on cheap TV sticks: check new
  animations in lite mode (`/tv?mode=lite`).
- **No new dependencies** without a good reason.
- **Nothing private in commits or screenshots**: no real IP addresses,
  emails, keys or channel names. Use placeholders like `<server-ip>`.
- Add a line to [CHANGELOG.md](CHANGELOG.md) for anything a user would
  notice.

## Releasing (maintainers)

1. Bump `VERSION` in `app/server.py` and add the version to the changelog.
2. Push to `main`: GitHub builds `ghcr.io/ttv-vibesbyvince/vibes-tv` as
   `:latest` and `:<version>`.
3. Publish a GitHub release tagged `v<version>` with the changelog entry.
