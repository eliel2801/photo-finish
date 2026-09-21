# The Agent Index listing

What the public listing says, kept here so it is versioned rather than typed
from memory into a web form at two in the morning. The Index stores these
fields: `name`, `blurb`, `repo`, `runtime`, `install_url`, `media`,
`use_cases`, `stories`.

---

## name

```
Photo Finish
```

## blurb

One line, and it has to survive being read in a list next to sixty others.

```
Watches the Agent Index and texts you only when your standing actually moves.
```

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

`docs/assets/` holds the screenshots this listing points at. Each one needs a
caption; the Index renders it underneath.

| file | caption |
| --- | --- |
| `photo-finish-alert.png` | `One install, one message. The other seventy-one runs that day sent nothing.` |
| `photo-finish-standing.png` | `Asked on demand: position, gap, and time left in one line.` |
| `photo-finish-countdown.png` | `One of four countdown marks on the final day, with what it would take to move up.` |

Capture these from the real conversation after deploy. A mock is worse than
none: the one thing this listing is claiming is that the agent is quiet, and a
staged screenshot cannot show seventy-one messages that were never sent.

---

## What this listing must not say

No claim about the official ranking formula. The hosts rank by installs **and**
token usage and have not published the weighting — this agent orders by installs
and says so, every time it matters. A listing that implies it knows the real
result is inventing one, and the hosts read these.
