---
name: pf-final
description: The last day and the result — fires a countdown mark at 24h, 12h, 6h and 1h before the hackathon snapshot, and posts the final board once after it. Runs hourly as the `pf-countdown` cron and does nothing on almost every run. Each mark is recorded so a restart, a rebuild or a double-fired cron cannot send it twice. Use when the pf-countdown cron fires, when the owner asks how long is left, or when they ask to see what a countdown alert looks like.
---

# Photo Finish — the final marks

```
python3 /opt/hermes/skills/pf-final/scripts/countdown.py
```

Runs hourly. Prints `nothing due (...)` almost every time, and on those runs
you do nothing at all — no post, no summary, no acknowledgement.

## The four marks

24h, 12h, 6h, 1h before the snapshot, then the final board once the snapshot
has passed.

Four interruptions across the last day is the most this earns. An hourly
countdown gets muted by the second day, and a silent agent on the last day
missed the only hours that mattered — the marks are the line between those two
failures.

Crossing two marks at once, after a restart or a long gap, sends **one**
message for the tightest one. Every mark above it is recorded as spent, so
nothing replays.

## What each mark carries

Time left, the owner's position and installs, what it would take to pass the
place above, and the podium. Plus one line that only appears while it is still
true: **not verified yet**. That is the gate that disqualifies quietly, and
the last day is when it stops being fixable.

## Output handling

| it printed | you do |
| --- | --- |
| `nothing due (...)` | Nothing. |
| `final already sent` | Nothing. |
| nothing / a sent message | The script posted it. Do not send a second. |
| an error | Do not post to the owner; report it in your final response for the log. |

## Showing the owner what a mark looks like

```
python3 /opt/hermes/skills/pf-final/scripts/countdown.py --force 6
python3 /opt/hermes/skills/pf-final/scripts/countdown.py --force final
```

`--force` takes `24`, `12`, `6`, `1` or `final`, and refuses anything else
rather than inventing a mark. It always prints and never sends, and records
nothing — a preview cannot spend a mark that has not come due. It renders the
mark it is simulating, not the current hour, so `--force 1` shows the owner
the one-hour message today.

## The clock this counts against

`snapshot_at` in `/var/lib/hermes/pf/config.json`, defaulting to
`2026-09-22T20:00:00Z`. The Luma listing's body says one day later than its own
end time; this counts to the earlier one on purpose. `pf-setup --snapshot-at`
changes it if the hosts confirm otherwise.

## State

Marks live in `marks_sent` inside `/var/lib/hermes/pf/state.json`, the same
file `pf-watch` writes its board snapshot to. Both writers merge rather than
replace — `pf_core.remember()` exists for exactly that reason. Never write
that file by hand, and never clear it to "re-test" a mark; use `--force`.
