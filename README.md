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

**Installing this rather than reading it? [INSTALL.md](INSTALL.md) is the full
walkthrough** — prerequisites, the Plow line, the three variables that matter,
troubleshooting, and how to uninstall. It assumes you have none of it yet.

The short version, for someone who already runs Plow agents. The Agent Index
usage reporter is built into this image — see below, because the base does not
provide it and a great many entries are going to discover that late.

```bash
git clone https://github.com/eliel2801/photo-finish.git
cd photo-finish

plow-agents login
plow-agents lines                 # pick one showing `free`
plow-agents mint ln_xxx           # writes plow-credentials
# ... append the three AGENT_* variables below, THEN:
docker compose up -d
```

Not `plow-agents deploy --local`, convenient as it is: it mints and starts
Compose in one move, and the three variables have to be written between those
two. A container that boots without `AGENT_ID` registers a listing nobody can
correct from inside it.

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

## Publishing it to the Index

**The base image does not carry the usage reporter.** Measured inside the built
image, on the base digest this Dockerfile pins: there is no `/opt/plow`, no
`agent-index-client.py`, and the supervision tree holds `dashboard`,
`hermes-gateway`, `home-guard`, `main-hermes` and `plow-init` — nothing that
reports anything. `plow-init` publishes `AGENT_ID` into the container
environment and nothing consumes it.

The Index's own publish-an-agent instructions say as much in step 3: *bake the
reporter into your image with `AGENT_ID=<your-agent-id>` — copy the agent-index
service from the example.* This repo does that. `vendor/client.pin` names a
commit of `plow-pbc/agent-index-client` and the build refuses any file that
does not hash to the value beside it; `image/s6-overlay/` carries the service
that runs it every five minutes.

That is what satisfies the hackathon's "must use the AI Worth Using client"
rule, and it is worth saying plainly what its absence looks like: an agent that
boots, answers every text, polls on schedule, and scores nothing — no
registration, no install counted, zero tokens on a board ranked by installs
**and** usage. It looks exactly like a working agent.

The reporter reads three variables from the credential file, and **all three
matter**:

```bash
cat >> plow-credentials <<'VARS'
AGENT_ID=photo-finish
AGENT_NAME=Photo Finish
AGENT_BLURB=Watches the Agent Index and texts you only when your standing moves.
VARS

docker compose up -d
```

- `AGENT_ID` — without it the reporter stands down entirely. Nothing is
  reported, nothing registers, and the agent looks like it is working.
- `AGENT_NAME` / `AGENT_BLURB` — optional, and **unset is not a blank page**:
  the Index stores the slug as the name and an empty blurb, permanently, and
  the builder cannot discover this from inside the container. Two agents on the
  live board are sitting there right now under a bare lowercase slug with no
  description. Set them before the first boot that registers.

After the restart the client registers the listing on its own.

### Point the listing at the install instructions

Registration alone leaves `install_url` empty, and the Index then shows the
owner a notice saying the agent was never configured — where a visitor expects
an **installs** link. Set it explicitly, once, from inside the container:

```bash
find / -name 'agent_index_client.py' 2>/dev/null     # confirm the path in your base image
set -a; . ./plow-credentials; set +a
python3 <path>/agent_index_client.py --register --agent 'photo-finish' --install-url 'https://github.com/eliel2801/photo-finish/blob/main/INSTALL.md'
```

Register **once**. Running this against a second slug does not rename the
listing, it creates another one, and two listings of the same agent split the
installs between them.

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
| `INSTALL.md` | the install, for someone who has none of this yet |
| `Dockerfile` | the base image, a persona, five skills, the usage reporter |
| `vendor/client.pin` | the Agent Index client, pinned by commit and checksum |
| `image/s6-overlay/` | the `agent-index` service, reporting every five minutes |
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

The Luma listing **ends** `2026-09-22T20:00:00Z`. The body of that same listing
says **"September 23rd, 1pm PT"**. One day apart.

The hosts settled it on their own site: the hackathon card on the Agent Index
reads **"final ranking Sep 23"**. This counts to that — `2026-09-23T20:00:00Z`,
1pm PT being UTC-7 in September.

It used to default to the earlier instant, on the reasoning that a countdown
running early costs a nudge and one running late costs the prize. That
undersold it. A countdown reaching zero posts the **final board**, records the
mark, and prints "final already sent" on every run afterwards — so the earlier
default would have announced the result with a day still on the clock and then
gone silent through the only day that mattered.

To point it somewhere else:

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
