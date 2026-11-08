# Be right back

Step away for a few minutes and leave chat something to do. The BRB screen
says **Be right back** with a countdown, and chat plays games by typing in
Twitch chat. When you're back, it shows what chat got up to.

It needs [Connect Twitch](install.md#connect-your-twitch-account-optional):
the games read your chat. Without it the screen still shows, with the
countdown, but no games.

## Add it to OBS

1. Make a **BRB scene** with a **Browser** source, **1920 x 1080**, at
   `http://<server-ip>:8777/brb`.
2. That's it. It sits on "Hang tight, chat" until you start a break.

It also shows on the TV while you're away, so it's on camera behind you if
your TV is. Alerts still play on top of it. Turn that off with Settings >
Be right back > **Show it on the TV too**.

## Start and end a break

| How | Start | Back |
| --- | --- | --- |
| Settings > Be right back | **Start BRB** (with the minutes next to it) | **I'm back** |
| Stream Deck or MixItUp (a web request) | `/brb/start` or `/brb/start?minutes=5` | `/brb/back` |
| Twitch chat (you and your mods) | `!brb` or `!brb 5` | `!back` |

- The countdown is 10 minutes unless you say otherwise (Settings changes the
  default). When it runs out and you're still away, it says **Back soon**.
- **I'm back** shows the welcome-back screen for 45 seconds (you can change
  it), then the BRB screen goes back to waiting. `/brb/stop` (or **Hide
  now**) hides it straight away, without the welcome back.
- Starting again while you're already away just resets the countdown.

## The games

**Guess when I'm back** runs the whole time, alongside the others. Chat
types `!guess 8:42`: minutes and seconds after you left. One guess each,
and guesses for a time that's already passed don't count. The closest guess
gets the crown when you're back.

The others take turns in the middle of the screen. Between games, chat
votes for the next one by typing `1` to `4` (20 seconds), or set **How the
next game is picked** to **Take turns** or **Just one**.

| Game | How chat plays | A game is |
| --- | --- | --- |
| Chat paints a picture | `!paint C4 pink`: a letter (A to Z), a number (1 to 15) and a colour. One pixel every 5 seconds each. `erase` clears a pixel. | 3 minutes (you can change it) |
| Trivia about you | Answer in chat. The first message with a right answer in it scores. | 10 questions, 20 seconds each |
| Typing race | Type the sentence exactly (capitals and punctuation don't matter). The first three score. | 8 sentences, 30 seconds each |
| This or that | `1` or `2` (or the option's name). One vote each. | 10 questions, 35 seconds each (30 to 40 recommended) |

Questions are shuffled, and nothing repeats until every question in the list
has been asked.

Colours for painting: pink, purple, gold (or yellow), green, orange, white,
blue, red and black.

## Your questions

Settings > Be right back > **Questions**, one per line:

- **Trivia**: `Question = answer, another answer | what the screen shows`.
  For example:

  ```
  What's {name}'s coffee order? = caramel macchiato, macchiato | Caramel macchiato, with soy milk
  ```

  A message counts as right if it has any of the answers in it. Capitals and
  punctuation don't matter, so `in n out` also matches "In-N-Out!". A
  question with nothing after `=` is kept but not asked, so you can fill the
  answers in over time. `{name}` is your name (Settings, or your Twitch
  name).
- **This or that**: `Coke | Pepsi`, or with a question:
  `Pineapple on pizza: Yes | No`.
- **Typing race**: one sentence per line.

Vibe TV starts you off with 39 trivia questions (you add the answers), 45
this-or-thats and 30 typing sentences. **Add back any starter questions I
deleted** puts back the ones you've removed.

## Welcome back

When you're back, the screen shows:

- who guessed closest, and how far off they were
- chat's painting
- the trivia champ, the fastest typist and the top painter
- **Chat has decided**: each this-or-that with the winner, like
  "Coke over Pepsi 71%", five at a time

Chat's painting also goes in the [end credits](credits.md), as *Chat's
masterpiece*. Turn that off with Settings > Credits > *Chat's painting*.

## Good to know

- Vibe TV only reads chat; it doesn't post in it. Everything shows on the
  screen.
- The games read Twitch chat only (not TikTok).
- A server restart in the middle of a break ends the break.
