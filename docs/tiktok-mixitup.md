# TikTok to MixItUp

When something happens on your [TikTok LIVE](tiktok.md), Vibe TV can run a
MixItUp command, so your sounds, chat messages, counters and the rest work for
TikTok too. It runs alongside the Vibe TV alert, not instead of it.

| TikTok event | When the command runs |
| --- | --- |
| New follow | Once per person (follow and unfollow spam doesn't run it again for an hour) |
| New subscriber | Every subscription and resubscription |
| Gift | When a combo ends, if it's worth at least the coins you set (combo total) |
| Share | Once per person every 5 minutes |
| Chat command, like `!blue` | When someone types it in chat (see [Chat commands](#chat-commands)) |

Leave an event on **None** and nothing extra happens.

## What the command gets

In MixItUp, use these in the command's actions (chat messages, text to
speech, overlays and so on):

| Special identifier | What it is |
| --- | --- |
| `$tiktokname` | Their TikTok name, like `Dance Queen 💃` |
| `$tiktokuser` | Their @handle, without the @ |
| `$tiktokavatar` | A link to their profile picture |
| `$tiktokevent` | `follow`, `sub`, `gift` or `share` |
| `$tiktokmonths` | Subs: how many months |
| `$tiktokgift` | Gifts: the gift's name, like `Rose` |
| `$tiktokgiftcount` | Gifts: how many in the combo |
| `$tiktokcoins` | Gifts: the combo's total in coins |

`$arg1text` is their @handle as well. A good place for these commands is a
**Custom** command group in MixItUp (they don't need a chat trigger).

## Chat commands

MixItUp only reads Twitch chat (and the other platforms it connects to), so
it doesn't see `!blue` typed in TikTok chat. Vibe TV does: under **Chat
commands** on the TikTok tab, **Add a chat command** for each one, with:

- **the word**: `!blue` (letters, numbers and `_`, any case; people can type
  it in any case too)
- **the MixItUp command** it runs. It can be the same one your Twitch `!blue`
  uses, so both chats do the same thing.
- **a cooldown** in seconds: how long before anyone can use it again (10 to
  start with; 0 for none)

The message has to start with the word. Anything typed after it is passed
along:

| Special identifier | What it is |
| --- | --- |
| `$tiktokmessage` | Everything after the command (`!blue please` gives `please`) |
| `$arg1text`, `$arg2text`, ... | Its words, one by one, like a Twitch chat command |
| `$tiktokcommand` | The command's word, without the `!` |
| `$tiktokname`, `$tiktokuser`, `$tiktokavatar` | Who typed it |
| `$tiktokevent` | `chat` |

Each person also waits 3 seconds between commands, so one person can't spam
them. Text to speech never reads messages that start with `!`.

**Pretend chat** (under the test buttons) sends a message as if someone typed
it in TikTok chat, and says whether it ran, or why not (not saved yet,
cooling down). It runs the real command.

## Set it up

### 1. Turn on MixItUp's Developer API

In MixItUp: **Services > Developer API > Connect**. MixItUp then answers on
port 8911, but only to programs on the same PC.

### 2. Let the NAS reach it (once, on the PC that runs MixItUp)

Vibe TV runs on your NAS, so the PC forwards a second port to MixItUp. Open
**PowerShell as administrator** on the PC (Start, type PowerShell, right-click
it, **Run as administrator**) and run these two commands. Put your NAS's
address in place of `NAS-ADDRESS` (the same one you use for the Vibe TV
settings page, without `http://` or the port):

```powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8912 connectaddress=127.0.0.1 connectport=8911
```

```powershell
New-NetFirewallRule -DisplayName "MixItUp for Vibe TV" -Direction Inbound -Protocol TCP -LocalPort 8912 -RemoteAddress NAS-ADDRESS -Action Allow
```

The first makes port 8912 pass requests on to MixItUp. The second lets only
your NAS through Windows Firewall to it. MixItUp's Developer API has no
password, so keep that `-RemoteAddress`. Both stay set after a restart.

Give the PC a fixed address on your network (in your router, often called a
DHCP reservation), so the NAS can always find it.

To undo it later:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8912
```

```powershell
Remove-NetFirewallRule -DisplayName "MixItUp for Vibe TV"
```

### 3. Pick the commands

Settings > **TikTok** > **MixItUp commands**:

1. **MixItUp's address**: `http://` and the PC's address, with `:8912`, then
   **Save settings**.
2. **Load commands**: the pickers fill with your MixItUp commands, grouped
   by type.
3. Pick a command for each event you want, set the coins for gifts, and save.
4. Try it with the **Test** buttons in that section. They play the alert and
   run the real command, so you'll see (or hear) it in MixItUp.

The chip beside the heading shows **Ready**, or **Problem** with what went
wrong on the last try (for example, MixItUp isn't open, or the command was
deleted). The line under the test buttons says what ran last.

## When it doesn't work

- **"Couldn't reach MixItUp"**: is MixItUp open, with the Developer API
  connected? Check the address and port 8912, and that the two commands above
  ran without an error (in PowerShell as administrator).
- **"MixItUp answered 404"**: the command was deleted or recreated in
  MixItUp. Load commands again and pick it.
- **Nothing happens, and the status shows it ran**: the command might be off
  in MixItUp (its picker says "off in MixItUp"), or its actions use
  requirements, like a cooldown, that aren't met.
- TikTok events need [TikTok LIVE](tiktok.md) switched on and connected.
