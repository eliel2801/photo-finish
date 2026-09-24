---
name: pf-shared
description: Shared plumbing for the Rank Alarm skills — reading the AI Worth Using Agent Index, ranking it, remembering the last read, posting a message to the owner, and registering the background crons. Not a skill the owner invokes; read it before changing how any other pf- skill talks to the Index or to Plow Chat, or when a pf- script fails and you need to know which layer broke.
---

# Rank Alarm — shared

Nothing here is invoked by the owner. It is the layer the four real skills sit
on, and the rules it enforces are the ones that make this agent worth keeping
installed.

## `pf_core.py` — the Index, read and remembered

Read the board, rank it, diff it.

- `fetch_agents()` / `fetch_usage(agent_id)` — the two public endpoints. No
  credential: the leaderboard is open.
- `standings(agents)` — ordered by installs, **competition ranking**: ties
  share a position and the next one skips (1, 2, 3, 3, 5). Four agents on two
  installs are all #4, which is what the owner sees on the site.
- `ahead_of(rows, me)` — the nearest row above and what it would take.
- `hours_left(config)` / `humanize_left(hours)` — the clock.
- `remember(rows)` — **use this, never `save_state(snapshot_of(...))`.** One
  state file, two writers: the poll rewrites the board every 20 minutes and the
  countdown records its spent marks. A blind save erases `marks_sent` and
  replays the whole final day's alerts, hour after hour, on the one day nobody
  wants to mute this agent.

A failed read **raises**. A poll that cannot see the Index retries on the next
tick; it never posts a standing built from half an answer.

A corrupt state file raises too. Reading it as empty would replay every alert
already sent.

## `pf_chat.py` — the one way to reach the owner

```
POST {PLOW_API_BASE}/v1/chats/{PLOW_HOME_CHANNEL}/messages
Authorization: Bearer {PLOW_AGENT_TOKEN}
{"body": "..."}
```

All three come from the container environment, which first boot publishes from
the credential the host dropped in. Never from a file the agent can write —
that is not a place to look for the API base its own bearer is sent to.

The bearer never appears in argv and never follows a redirect: a 302 to
another host with a token attached is how a token leaves the building.

`send(text, dry_run=True)` prints instead of posting. Every producer takes a
`--dry-run` flag that routes here.

## Why no producer uses `cron --deliver`

That arm relays every final response, no-ops included. Both producers here are
quiet by design — they run, usually find nothing, and post for themselves when
they do. A `--deliver` on the watch row would text its owner "no change"
seventy-two times a day.

Leaving `--deliver` off is not enough on its own: a Hermes cron job still
delivers its final response to the chat it was created from, and only a final
response of exactly `[SILENT]` suppresses it. So every cron run of these skills
ends on `[SILENT]`. The live agent proved it: runs that echoed `no change`
reached the owner as a "Cronjob Response: pf-watch" text.

This is the single most important fact in this repo. If a new producer is
added, it posts through `pf_chat`; it does not take a deliver arm.

## `register_crons.py` — two rows, idempotent

Reads `/var/lib/hermes/cron/jobs.json` — hermes' own state, where a name is a
field — rather than parsing `hermes cron list`. The only absence that means
"nothing is registered" is the file not existing; anything else stops, because
re-registering on a bad read duplicates every job and a cron has no undo.

A paused row is left paused. Re-creating it duplicates it, and resuming it
silently undoes a decision somebody made on purpose.

## Files

| path | holds | written by |
| --- | --- | --- |
| `/var/lib/hermes/pf/config.json` | `agent_id`, optional `snapshot_at` | `pf-setup` |
| `/var/lib/hermes/pf/state.json` | last board read, `marks_sent` | `pf-watch`, `pf-final` |

Both live in the agent's home volume and survive rebuilds. Neither carries a
credential, a chat id or anything about a person.
