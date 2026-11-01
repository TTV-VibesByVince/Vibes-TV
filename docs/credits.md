# End credits

[← Back to the README](../README.md) · [All docs](README.md)

Movie-style credits for the end of your stream: everyone who followed,
subbed, gifted, raided, cheered or chatted for the first time, a thank-you
to your mods, with their profile pictures, then your logo. They can sit
invisibly on top of your stream until you play them, or have a scene of
their own.

They're Twitch only: TikTok follows, subs and gifts are left out (the
[TikTok widgets](tiktok.md#widgets-for-obs) cover those all stream).

## Add them to OBS

The credits have their own address: `http://<server-ip>:8777/credits`. Add
it as a **Browser** source, **Width 1920**, **Height 1080**. Then pick one of
two ways to use it:

**On top of your main scene (recommended).** Settings > Credits: **When they
start** = *Only when /credits/play is called*, **When they finish** = *Fade
away*. The source stays invisible all stream. When you call `/credits/play`
(a Stream Deck button, or a MixItUp command like `!credits`), they take over
the whole screen, roll, then fade away and your stream is back.

**In an "Ending" scene.** **When they start** = *When the source appears*,
and in OBS tick **Refresh browser when scene becomes active**, so they roll
from the top each time you switch to the scene. **When they finish** = *Stay
on the end card* (or *Start again* to loop).

`/credits/play` starts them again on every open credits page, either way.

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

## Animations

Each list can have its own animation as it rolls in (on by default; untick
**Animation** next to a list to turn it off). They play behind the names, so
the names stay readable.

| List | Animation |
| --- | --- |
| Thank you to the mods | Two swords swing in and cross with a slash of light, like the mod badge |
| Thank you to the VIPs | Sparkles, then a shower of pink gems, like the VIP badge (VIPs also get pink rings) |
| Raided by | Police lights sweeping, and hazard tape across the top and bottom |
| New subscribers / Resubscribed | A burst of stars |
| Gifted subs | Gift boxes raining down |
| Cheered | Gems in Twitch's cheer colours raining down |
| Watch streaks | A wall of fire along the bottom |
| New followers | Hearts floating up |
| First time in chat | Waving hands popping up |
| Hype train | A train crossing the screen |
| This stream | Confetti cannons |

## With Twitch connected

**Settings > Setup > Connect Twitch** ([how](install.md#connect-your-twitch-account-optional))
makes the credits look after themselves:

- **Mods and VIPs** who chat are added by themselves, from their badges. No
  Entrance Commands needed.
- **A new list starts when you go live** (Settings > Credits > *Start a new
  list when I go live*). No Stream Start request needed.
- **Fill the credits from: Twitch directly** takes follows, subs, resubs,
  gifted subs (with who got them), cheers, raids, watch streaks, gigantified
  emotes and the hype train level straight from Twitch, so the credits don't
  depend on MixItUp's events. Your alerts still play from MixItUp as before,
  and nobody is counted twice. **First-time chatters** still come from
  MixItUp's `/welcome`: Twitch's live events don't say who's new.

## Set it up in MixItUp

Not needed for anything Connect Twitch already does (above).

**A new list each stream.** In MixItUp's **Stream Start** event, add a Web
Request action:

```
http://<server-ip>:8777/credits/reset
```

(**Settings > Credits > Start a new list** does the same.)

**Your mods.** Without Connect Twitch, Vibe TV doesn't see chat, so the mods tell it they're here:
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
| Background | **Dark** (your theme's particles drifting up), **Starfield** (flying through stars), **Neon grid** (a synthwave sun over a moving grid), **Aurora** (glowing colour waves), **Your logo** (blurred and darkened, like the TV) or **See-through** (over your stream). |
| When they start | **When the source appears** (or the scene is switched to), or **Only when /credits/play is called**. |
| When they finish | **Fade away** (back to see-through: your stream is back), **Stay on the end card**, or **Start again** (loop). |

The end card shows your logo (from the Logo section) for 7 seconds before
the credits fade away or loop (or for good, with *Stay on the end card*).
The credits use your theme's colour and particles, so they turn spooky in
October with the Halloween theme.

## Good to know

- The list is saved on the server, so a restart mid-stream doesn't lose it.
- Each person is listed once per list, however many times they cheered or
  gifted (the amounts add up).
- The live preview on the Credits tab shows them with sample names, and
  follows your changes **before you save**, so you can try backgrounds and
  animations. **Replay preview** starts just the preview again (the credits
  in OBS aren't touched). Untick **Show sample data** to see this stream's
  real list.
