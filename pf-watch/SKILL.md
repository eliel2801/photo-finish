---
name: pf-watch
description: Poll the AI Worth Using Agent Index and text the owner ONLY when their standing moved — installs gained or lost, someone overtook them, someone they overtook, position changed. In spectator mode it speaks only when the podium changes. Runs every 20 minutes as the `pf-watch` cron; the script posts for itself and prints "no change" when there is nothing to say. Use when the pf-watch cron fires, when the owner asks to check for changes right now, or when the owner asks why they have not heard anything.
---

# Rank Alarm — the watch

Run the poll. Let it decide. Say nothing it did not say.

**As a cron run, your final response is exactly `[SILENT]`** unless the script
failed. Hermes texts every other final response to the owner as a
"Cronjob Response" -- a reply of `no change` becomes an SMS saying `no change`.

```
python3 /opt/hermes/skills/pf-watch/scripts/poll.py
```

That is the whole skill. The script reads the Index, diffs it against the last
read, posts to the owner through Plow Chat if the standing moved, and saves the
new baseline.

## What you do with its output

| it printed | you do |
| --- | --- |
| `no change (...)` | Reply `[SILENT]`. Do not post, do not summarize, do not echo it. |
| `baseline saved: ...` | Reply `[SILENT]`. First run after setup; there was nothing to compare against. |
| `snapshot passed, the watch is off` | Reply `[SILENT]`. The board is frozen; pf-final sent the result. |
| `would save baseline: ...` | Nothing. A `--dry-run` on a home with no state yet; nothing was written. |
| nothing / a sent message | Reply `[SILENT]`. The script already texted the owner; a second copy is noise. |
| a traceback or an error line | Do not post to the owner. Report it in your final response so the cron log carries it. |

The one mistake this skill exists to prevent: composing your own "still #4"
message after a quiet run. That is the behaviour that gets this agent muted,
and a muted agent is worthless to its owner during a race.

## Why `[SILENT]`, and why no `--deliver`

A Hermes cron job delivers its final response to the chat that created it,
with or without `--deliver`; only a final response of exactly `[SILENT]` stops
it. This producer posts for itself through `pf_shared/pf_chat.py`, so the
agent's own reply must never reach the owner. If you ever register this cron
by hand, register it without `--deliver`.

## Asked for a check right now

Same command. This is a conversation, not a cron run, so `[SILENT]` does not
apply. If it prints `no change`, tell the owner exactly that in one
line — a direct question deserves a direct answer, and answering a question is
not an interruption.

## Flags

- `--dry-run` — print the message that would be sent, send nothing, save
  nothing. Use when the owner wants to see what an alert looks like.
- `--report` — print the top of the board and exit. No diff, no post.

## State

- `/var/lib/hermes/pf/config.json` — `agent_id` (absent means spectator mode),
  optional `snapshot_at`.
- `/var/lib/hermes/pf/state.json` — the previous read, plus the countdown's
  spent marks. Shared with `pf-final`; never write it by hand.

Deleting `state.json` makes the next run a silent baseline, not a flood. That
is the safe way to reset if the owner thinks the alerts drifted.
