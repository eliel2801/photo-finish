---
name: pf-standing
description: Answer "where am I?" on demand — the owner's position on the AI Worth Using Agent Index, their install count, how many installs would take the place above, how long is left before the snapshot, and optionally reported token usage and the top of the board. Prints its answer; posts nothing, because the owner is already in the conversation that asked. Use whenever the owner asks about their rank, position, install count, token usage, who is ahead, how much time is left, or how the leaderboard looks.
---

# Photo Finish — the standing

```
python3 /opt/hermes/skills/pf-standing/scripts/standing.py
```

Relay what it prints. It is already written to be read aloud in a text
message: position, gap, clock. Do not pad it with a greeting or restate it in
your own words — every line it prints is a number from the live Index, and
rephrasing numbers is how numbers get wrong.

## Flags

- `--top N` — how many rows of the board to include. Default 5. Use 3 when the
  owner just wants the podium.
- `--tokens` — also fetch reported token usage. One extra request per row
  shown, so it is off by default. Use it when the owner asks about tokens, or
  when they are close enough to the top that the second ranking signal matters.

## The gates

The script prints a `Gates:` line when the owner's listing is missing something
that decides the race independently of install count:

- **Not verified.** An unverified agent cannot win, whatever the board says.
  The fix is a human on the hosts' Discord, and the queue is the bottleneck —
  so this is the one gate worth raising early and repeating.
- **Not deployable.** No one-click install from the leaderboard.
- **No video.** Among the agents with 2+ installs on this board, the large
  majority carry a video on the listing; among those with 0 or 1, about half
  do. The listing is what converts a viewer into an install.

Say the open gates plainly, once, then drop it. Repeating them every message
is nagging, and the owner will stop reading.

## If the owner asks about the official ranking

Say what is true: the hosts rank by installs **and** token usage, and the
weighting is not published. This board orders by installs. Never present it as
the official result.

## If the script fails

Say it failed and stop. Do not answer from memory, do not carry a number from
earlier in the conversation, do not estimate. In a race decided by single
installs, a stale number is worse than no number.
