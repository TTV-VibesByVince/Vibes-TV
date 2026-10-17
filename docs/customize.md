# Make it yours

Text, colours, themes and backups, all from the settings page (`/admin`).

[← Back to the README](../README.md) · [All docs](README.md)

## Text

Settings > **Text & colours** has a box for every line on every screen.
Leave a box empty to keep the default. Placeholders like `{name}`,
`{months}`, `{amount}`, `{tier}`, `{count}`, `{viewers}`, `{game}` and
`{level}` are filled in (each event lists the ones it has). Text in
`[square brackets]` only shows when its placeholder has a value, so
`[Last seen playing {game}]` disappears for someone with no game.

## Colours

Each event's colour drives its glow, accents and your lights:

- **Avatar colour** (default): picked from their profile picture.
- **Theme colour**: the current theme's colour (e.g. orange at Halloween).
- **Custom**: any colour you choose.

## Themes

Settings > **Theme**. A theme changes the confetti, the shapes that float up
on the follow screen, the raid's warp colours and the theme colour.

| Theme | Floats | Colour |
| --- | --- | --- |
| Vibe (default) | hearts | purple |
| Halloween | bats | orange |
| Winter holidays | snowflakes | red |
| Valentine's | hearts | pink |
| St Patrick's | clovers | green |

Click one to switch every TV at once. Under **Schedule**, add date ranges
(they repeat every year) and the theme turns itself on and off; **Add the
holiday presets** fills in sensible dates. A scheduled theme beats the one
you clicked while its dates last.

## Backup

Settings > **Backup** downloads every setting in one JSON file (the Twitch
secret only if you tick the box) and restores it again, e.g. after
reinstalling. Logo files aren't in it: they live in the `media` folder.
