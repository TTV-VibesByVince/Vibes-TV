# End credits

[← Back to the README](../README.md) · [All docs](README.md)

Movie-style credits for the end of your stream: everyone who followed,
subbed, gifted, raided, cheered or chatted for the first time, a thank-you
to your mods, with their profile pictures, then your logo. Put them in an
"Ending" scene in OBS.

## Add them to OBS

1. Add a **Browser** source with `http://<server-ip>:8777/credits`, **Width
   1920**, **Height 1080**.
2. Tick **Refresh browser when scene becomes active**, so they roll from the
   top each time you switch to the scene.

`/credits/play` starts them again on every open credits page, for example
from a Stream Deck button or a MixItUp command.

## Who's in them

Everyone from your alerts is remembered automatically, once per list, with
their picture (from your Twitch API keys, or MixItUp's `&avatar=`). There's
nothing extra to set up for follows, subs, resubs, gifted subs, cheers,
raids, watch streaks, first-time chatters, gigantified emotes or the hype
train. Test alerts from the settings page aren't remembered.

| List | From |
| --- | --- |
| Thank you to the mods / VIPs | `/credits/seen` (see below) |
| Raided by | Raids, with their viewer counts added up |
| New subscribers / Resubscribed | Subs (with the tier) and resubs (with the months) |
| Gifted subs | Each gifter, with everyone they gifted to |
| Cheered | Bits, added up per person |
| Watch streaks | The longest streak each person shared |
| New followers | Follows |
| First time in chat | `/welcome` pop-ups |
| Gigantified | Who gigantified, with the emotes |
| Hype train | The highest level reached |
| This stream | Counts: new followers, subs, gifted subs, raids, bits, first-time chatters |

Lists with nobody in them are left out. Untick any list under **Settings >
Credits > What's in the credits**.

## Set it up in MixItUp

**A new list each stream.** In MixItUp's **Stream Start** event, add a Web
Request action:

```
http://<server-ip>:8777/credits/reset
```

(**Settings > Credits > Start a new list** does the same.)

**Your mods.** Vibe TV doesn't see chat, so the mods tell it they're here:
in MixItUp, open **Users**, pick a mod, and give them an **Entrance
Command** (it runs the first time they chat each stream) with a Web Request
action:

```
http://<server-ip>:8777/credits/seen/$username?role=mod&avatar=$useravatar
```

Do the same for VIPs with `role=vip`, and they get their own "Thank you to
the VIPs" list.

## Settings

Settings > **Credits**:

| Setting | What it does |
| --- | --- |
| Title | The big line at the top. "Thanks for watching!" by default. |
| Last line | Under your logo at the end. "See you next stream!" by default. |
| Speed | 0.3 (slow) to 3 (fast); 1 is about a twelfth of the screen a second. |
| Background | **Dark**, with your theme's particles drifting up, or **See-through**, over your stream. |
| Loop | Start again after the end card, instead of staying on it. |

The end card shows your logo (from the Logo section) and holds for 8 seconds.
The credits use your theme's colour and particles, so they turn spooky in
October with the Halloween theme.

## Good to know

- The list is saved on the server, so a restart mid-stream doesn't lose it.
- Each person is listed once per list, however many times they cheered or
  gifted (the amounts add up).
- The live preview on the Credits tab shows them with sample names; untick
  **Show sample data** to see this stream's real list.
