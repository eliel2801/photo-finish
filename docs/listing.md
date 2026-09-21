# The Agent Index listing

What the public listing says, kept here so it is versioned rather than typed
from memory into a web form at two in the morning.

## How it is actually published

Not through a form. The Index hands every builder the same standalone client
and the listing is one call to it:

```bash
curl -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/main/standalone/agent_index_client.py
set -a; . ./plow-credentials; set +a
python3 agent_index_client.py --register --agent photo-finish \
  --name "Photo Finish" \
  --blurb "Stop refreshing this leaderboard. It tracks your rank, the top 3 and who just passed you, and texts you the moment any of it moves. Silence when nothing did." \
  --repo "https://github.com/eliel2801/photo-finish" \
  --runtime hermes \
  --install-url "https://github.com/eliel2801/photo-finish/blob/main/INSTALL.md" \
  --video "<YOUTUBE_VIDEO_ID>" \
  --image "<RAW_URL_TO_A_SCREENSHOT>"
```

Three things about that call cost a gate if you get them wrong:

- **`--video` takes a YouTube video ID, never a URL.** The page embeds
  `youtube-nocookie.com/embed/<id>`, so a URL renders a broken player on a
  public page. The client refuses a value containing `/` or `:`; anything else
  it accepts and publishes. `has_video` is one of the three fields that is
  13/13 among the rows currently qualifying.
- **Register once.** Running it against a second id does not rename the
  listing, it creates another one, and two listings split the installs. On an
  id somebody else published, the client returns 409 and *joins* — the page
  stays theirs and all you get is a report key.
- **`AGENT_ID` must be baked into the image**, because the reporter reads it
  there. Without it nothing reports and the agent looks like it is working.

Check what the Index thinks before and after:

```bash
python3 agent_index_client.py status          # 0 registered, 3 not, 2 cannot tell
python3 agent_index_client.py --agent photo-finish --dry-run
python3 agent_index_client.py --self-check
```

## Why the token numbers need watching on Hermes specifically

The client collects usage from two places, and its own docstring says why:
agentsview — the index it shares with the Builder Index — **reports zero for
Hermes, with no fix known upstream.** It compensates by reading Hermes' own
store directly, `$HERMES_HOME/state.db`, where the shipped image sets
`HERMES_HOME=/opt/data` on the volume the container keeps.

Half the ranking is token usage. So `--dry-run` showing non-zero days is not a
nicety on this runtime, it is the check that the other half of the score is
being reported at all. Run it once after the first boot.

---

## name

```
Photo Finish
```

## blurb

One line, and it has to survive being read in a list next to sixty others.

```
Stop refreshing this leaderboard. It tracks your rank, the top 3 and who just passed you, and texts you the moment any of it moves. Silence when nothing did.
```

Live on the Index since 2026-09-21, set with `plow-agents image set photo-finish
--blurb`. That command edits a listing you own using the account token, so it
works with no container running -- the `--register` call needs a Plow agent
credential, this one does not.

## repo

```
https://github.com/eliel2801/photo-finish
```

## install_url

```
https://github.com/eliel2801/photo-finish/blob/main/INSTALL.md
```

## runtime

```
hermes
```

---

## use_cases

- **You are in this hackathon.** Your position changes at 3am and you find out at 9am. It texts you at 3am, and nothing at 4, 5, 6, 7 or 8.
- **Someone just installed your agent.** `+1 install. You are on 4.` — the one message you actually wanted a notification for.
- **Somebody passed you.** Named, with both numbers, while there is still time to do something about it.
- **You want the number without the tab.** Text it `where am I?` and get position, the gap to the place above, and time left, in one line.
- **You did not ship an agent.** Spectator mode follows the podium and the countdown anyway.
- **The last day.** Four countdown marks — 24h, 12h, 6h, 1h — each with what it would take to move up one place. Then the final board, once, and it stops.

## stories

**The 3am install.**
Someone in another timezone tried ReceiptSnap and it worked. The board moved at
03:12. Photo Finish sent one message: `+1 install. You are on 4. Up to #3 (was
#4).` Its owner read it at 08:40, over coffee, already knowing. They did not
refresh anything to find out.

**The seventy-one quiet runs.**
That same day the poll ran seventy-two times. Seventy-one of them found a board
that had not moved for that owner, and sent nothing at all. This is the entire
product. An agent that texts on a schedule gets muted, and a muted agent has
lost the race for the person who installed it.

**The pass you would have missed.**
`Founder Agent passed you (7 vs your 6).` Sent ninety seconds after it happened,
with 38 hours still on the clock — which is the difference between a thing you
can answer and a thing you read about afterwards.

---

## media

`docs/assets/` holds what the listing points at. All of it went up on
2026-09-21 with the account token and no container running: `plow-agents
image set photo-finish --screenshot URL` (repeated; the list is replaced, not
appended) for the images, and `POST /v1/agent-logo?agent_id=photo-finish`
with the same Index assertion `image set` uses for the logo, which `image set`
itself has no flag for.

| file | what it shows |
| --- | --- |
| `photo-finish-logo.png` | the listing's avatar: a checkered finish-line ribbon on green |
| `photo-finish-01-setup.png` | setup: one question, the row locked in, two jobs registered |
| `photo-finish-03-alert.png` | the alert, then nineteen hours of nothing |
| `photo-finish-02-standing.png` | asked on demand: position, gap, time left, the gates |
| `photo-finish-04-final.png` | a countdown mark on the last day, then the final board once |

The Index shows no captions, and renders the images as a two-column grid of
portrait tiles (189x358 px, cover-cropped), which is why these are phone-shaped
(1080x2044) rather than the square that the README's table would suggest.

The text in each screen is the scripts' own output against the live board on
2026-09-21; the alert is `poll.py --dry-run` with one install simulated. The
phone frame is a render. The README says so in as many words, because the one
thing this listing claims is that the agent is quiet, and a listing that
overstated its evidence would be the wrong place to start.

The three `--story` entries under USE CASES were posted the same way (the Index
accepts the account assertion on `/v1/stories` too); they describe what the
agent has actually done since setup and nothing it has not.

## video

`--video` still takes a YouTube ID. The demo is built (`photo-finish-demo.mp4`,
39.8 s, 1080p, eight slides rendered from `docs/assets`) and waits on an upload;
until the ID is set the row keeps its WIP badge no matter what else is on it.

---

## What this listing must not say

No claim about the official ranking formula. The hosts rank by installs **and**
token usage and have not published the weighting — this agent orders by installs
and says so, every time it matters. A listing that implies it knows the real
result is inventing one, and the hosts read these.
