# Photo Finish

**You are not going to stop refreshing the leaderboard. So stop refreshing the leaderboard.**

A [Hermes](https://github.com/NousResearch/hermes-agent) agent, texted from
iMessage over the Plow Chat platform, that watches the
[AI Worth Using Agent Index](https://aiworthusing.com/agent-index) on your
behalf during the Hermes Hackathon and texts you **only when your standing
actually moves**.

```
+1 install. You are on 4.
Up to #3 (was #4).
#2 Founder Agent is on 5; +2 would take it. 38h left to the snapshot.
```

And on every one of the seventy-odd runs a day where nothing happened, it
sends nothing at all.

## Why this exists

The board is public. Anyone can refresh it. Nobody can *stop* refreshing it —
which is the actual chore, and it is the one this agent does end to end.

## What it tells you

| when | what |
| --- | --- |
| someone installs your agent | `+1 install. You are on 4.` |
| someone passes you | `ReceiptSnap passed you (5 vs your 4).` |
| you pass someone | `You passed Hermes Cat Paw.` |
| your position moves | `Down to #6 (was #4).` |
| you ask | position, gap to the place above, time left, tokens if you want them |
| 24h / 12h / 6h / 1h out | one countdown mark, with what it would take to move up |
| after the snapshot | the final board, once |
| **nothing changed** | **nothing** |

No agent of your own yet? **Spectator mode** follows the podium and the
countdown. Registering for a hackathon and not shipping is common; being shut
out of watching it is not a good reason to uninstall something.

## Install

Built on a Plow base image, so the Agent Index usage client is already in it.

```bash
git clone https://github.com/<you>/photo-finish.git
cd photo-finish

plow-agents login
plow-agents deploy --local --line ln_p1
```

Then text it. It will ask which row on the Index is yours:

```
you  > photo finish
agent> Which agent is yours on the Index? Name or slug is fine — I can search
       on your builder name too.
you  > receiptsnap
agent> Locked in: ReceiptSnap (receiptsnap) — #4, 2 installs.
       4.1 days left to the snapshot. I'll text you when it moves.
```

Setup registers two background jobs and then gets out of your way.

## How it works

```
cron every 20 min
  └─ GET /v1/agents              ← public, no credential
     └─ diff against state.json  ← the last read, in the agent's home volume
        ├─ your standing moved?  → POST /v1/chats/{uid}/messages
        └─ it didn't?            → save and say nothing
```

That is the whole mechanism. One public endpoint, one JSON file, one
comparison. No Mac, no Latch, no browser, no paid API.

### The design decision everything else follows from

Hermes' `cron --deliver` relays every final response, **including the empty
ones**. A quiet producer cannot use it — it would text you "no change"
seventy-two times a day. So neither cron here takes a deliver arm; the scripts
decide for themselves and post directly through Plow Chat when, and only when,
there is something to say.

An agent that texts on a schedule gets muted. A muted agent is worthless
during a race.

## Layout

| path | what |
| --- | --- |
| `Dockerfile` | the base image, a persona, five skills |
| `runtime/persona.md` | who it is and how it speaks — short, English, never chatty |
| `pf-shared/` | Index reads, ranking, chat transport, cron registration |
| `pf-setup/` | which row is yours; spectator mode; the snapshot instant |
| `pf-watch/` | the poll — every 20 minutes, quiet unless it moved |
| `pf-standing/` | "where am I?", answered on demand |
| `pf-final/` | four countdown marks and the final board |

State lives in the agent's home volume, survives rebuilds, and carries no
credential, no chat id and nothing about a person:

- `/var/lib/hermes/pf/config.json` — `agent_id`, optional `snapshot_at`
- `/var/lib/hermes/pf/state.json` — the last board read, and spent marks

## Ranking, honestly

The hosts rank by installs **and** token usage, and the weighting is not
published. Standings here order by **installs**, with competition ranking
(ties share a position: 1, 2, 3, 3, 5). Token usage is a number you can ask
for — `--tokens` — not one this agent alerts on, because it moves
continuously and alerting on it would mean alerting always.

This agent never presents its install order as the official result.

## The snapshot instant

The Luma listing **ends** `2026-09-22T20:00:00Z`. The body of that same
listing says **"September 23rd, 1pm PT"**. One day apart. This counts down to
the earlier one, because a countdown that runs early costs a nudge and one
that runs late costs the prize.

If the hosts confirm the later one:

```bash
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --snapshot-at 2026-09-23T20:00:00Z
```

## Running the scripts outside the container

Every script takes `--dry-run`, and the Index endpoints need no credential, so
the logic is testable on any machine with Python 3.9+ and no Docker:

```bash
PF_HOME=./.pf-local python3 pf-watch/scripts/poll.py --report
PF_HOME=./.pf-local python3 pf-setup/scripts/setup.py --search "receipt"
PF_HOME=./.pf-local python3 pf-watch/scripts/poll.py --dry-run
PF_HOME=./.pf-local python3 pf-final/scripts/countdown.py --force 6
```

Only posting to Plow Chat needs the container's credential.

## License

MIT. See [LICENSE](LICENSE).
