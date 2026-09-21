# Installing Photo Finish

You are about to run a leaderboard watcher that texts you **only when your
standing on the AI Worth Using Agent Index actually moves** — and stays silent
on the seventy-odd runs a day where it doesn't.

This page assumes you have none of it yet: no Plow account, no credential, no
agent of your own on the Index, nothing of the author's. If a step needs
something you don't have, it says so before you start typing.

---

## Before you start

| you need | why | how long |
| --- | --- | --- |
| Docker Engine + Compose **2.24+** | the agent is a container | 10 min |
| a Plow account | the agent texts you through Plow Chat | 2 min |
| **one free Plow line** | every agent consumes one phone number | — |
| Python 3.9+ *(optional)* | only to try the logic before installing | — |

**About the line.** A Plow account holds roughly five or six lines, and they are
ephemeral rather than permanent allocations. If every one of yours is already
bound to another agent, minting fails with a message saying exactly that. Run
`plow-agents lines` to see which are `free`, and `plow-agents revoke ln_xxx` to
retire an agent on one you no longer run. Discovering this at deploy time is the
most common way this install runs long, which is why it sits at the top of the
page instead of down in troubleshooting.

**You do not need an agent of your own on the Index.** Photo Finish has a
spectator mode that follows the podium and the countdown. Registering for a
hackathon and not shipping is common; being shut out of watching it is not a
good reason to skip this.

---

## Try it before you install it

The Index endpoints are public and need no credential, so the entire watching
logic runs on any machine with Python — no Docker, no account, no commitment:

```bash
git clone https://github.com/eliel2801/photo-finish.git
cd photo-finish

PF_HOME=./.pf-local python3 pf-watch/scripts/poll.py --report
```

That prints the live board. Nothing is written outside `./.pf-local`, nothing is
sent anywhere, and you can delete the folder and walk away.

```bash
PF_HOME=./.pf-local python3 pf-setup/scripts/setup.py --search "your name"
PF_HOME=./.pf-local python3 pf-watch/scripts/poll.py --dry-run
PF_HOME=./.pf-local python3 pf-final/scripts/countdown.py --force 6
python3 tests/test_pf.py
```

Only posting to Plow Chat needs the container.

---

## 1. Clone

```bash
git clone https://github.com/eliel2801/photo-finish.git
cd photo-finish
```

## 2. Mint your own credential

```bash
plow-agents login          # prints a number and a phrase — text the phrase to it
plow-agents lines          # your lines, with IDs and availability
plow-agents mint ln_xxx    # the ID of a line showing `free`
```

`mint` takes the line ID as a plain argument, not a flag. `lines` marks a line
held by another account as `in use`, your own agents by their uid, and prints
`unknown` when the API is too old to say — treat `unknown` as "try it and see".

There is a one-step alternative, `plow-agents deploy --local --line ln_xxx`,
which mints the credential **and immediately starts Compose**. Do not use it
here. Step 3 has to happen between minting and the first boot, and that command
leaves no room between them — the container comes up before `AGENT_ID` exists
and registers a listing you cannot fix from inside it.

This writes a `plow-credentials` file in the working directory holding **your**
Plow endpoint and **your** agent token. It is yours alone: it is gitignored, it
never leaves your machine, and nothing in this repo reads it except Docker
Compose handing it to the container as environment.

If you keep credentials outside the checkout, point at it instead, and then a
`docker compose down -v` can never wipe it:

```bash
export PLOW_CREDENTIALS=/secure/path/plow-credentials
```

## 3. Set three variables — before the first boot

Append these to the credential file **now**, not after:

```
AGENT_ID=photo-finish
AGENT_NAME=Photo Finish
AGENT_BLURB=Watches the Agent Index and texts you only when your standing moves.
```

**Keep `AGENT_ID=photo-finish` exactly as written.** That value is what tells the
Index your install belongs to this agent — it is how the install is counted and
how the tokens your copy spends are attributed. Changing it customises nothing;
it quietly publishes a separate empty listing under a new slug, and your install
stops counting for the agent you meant to install.

The other two matter only if you are publishing a fork of your own. Leaving them
unset is **not** a blank page: the Index stores the slug as the name and an empty
blurb, permanently, and you cannot discover or fix this from inside the
container. Agents on the live board are sitting there right now under a bare
lowercase slug with no description because of exactly this.

## 4. Bring it up

```bash
docker compose up -d
docker compose logs -f agent
```

First boot publishes your credential into the container environment, starts the
Agent Index usage reporter as a supervised service, and mints this install's own
Agent Index key. A second boot does not mint again.

## 5. Text it

Send anything to your Plow line. It asks one question:

```
you  > photo finish
agent> Which agent is yours on the Index? Name or slug is fine — I can search
       on your builder name too.
you  > receiptsnap
agent> Locked in: ReceiptSnap (receiptsnap) — #7, 3 installs.
       38h left to the snapshot. I'll text you when it moves.
```

No agent of your own? Say so, and it offers spectator mode in one line.

Setup registers two background jobs — a poll every 20 minutes and an hourly
countdown check — and then gets out of your way. That is the whole install.

---

## What it will send you

| when | what |
| --- | --- |
| someone installs your agent | `+1 install. You are on 4.` |
| someone passes you | `ReceiptSnap passed you (5 vs your 4).` |
| you pass someone | `You passed Hermes Cat Paw.` |
| your position moves | `Down to #6 (was #4).` |
| 24h / 12h / 6h / 1h out | one countdown mark each, with what it would take to move up |
| after the snapshot | the final board, once |
| **nothing changed** | **nothing at all** |

Ask it `where am I?` any time and it answers on demand: position, gap to the
place above, time left, and token usage if you want that number.

It never texts you a schedule, a summary, or a "still #4". An agent that texts on
a schedule gets muted, and a muted agent is worthless during a race.

---

## Troubleshooting

| symptom | cause | fix |
| --- | --- | --- |
| `mint` fails saying lines are in use | all your lines are bound | `plow-agents revoke ln_xxx`, then mint again |
| `mint` rejects `--line` | the line ID is positional | `plow-agents mint ln_xxx` |
| container up, no reply to your text | credential minted for a different line | re-mint against the line you texted |
| it never speaks first | crons were never registered | run `register_crons.py` inside the container (below) |
| `PLOW_AGENT_TOKEN is unset` in logs | `plow-credentials` missing or empty | check `env_file` resolves; re-run `plow-agents mint` |
| a listing appeared under a bare slug | `AGENT_ID` was unset on first boot | set all three variables, then `docker compose up -d --force-recreate` |
| `state.json is unreadable` | a write was interrupted | delete `state.json` in the home volume; the next poll rebuilds the baseline |

```bash
docker compose exec agent python3 /opt/hermes/skills/pf-shared/scripts/register_crons.py
docker compose exec agent python3 /opt/hermes/skills/pf-setup/scripts/setup.py --show
```

`register_crons.py` is idempotent — it reads what hermes already has and creates
only what is missing, so it is safe to run whenever you are unsure.

## Changing what it watches

```bash
docker compose exec agent python3 /opt/hermes/skills/pf-setup/scripts/setup.py --agent-id <slug>
docker compose exec agent python3 /opt/hermes/skills/pf-setup/scripts/setup.py --spectator
```

Or just tell it in chat — that is what the setup skill is for.

## The snapshot instant

It counts down to `2026-09-23T20:00:00Z` — what the hackathon card on the Agent
Index calls the final ranking. The Luma listing's own end time is a day earlier
than its body text, and this follows the date the hosts publish where entrants
read it. To point it somewhere else:

```bash
docker compose exec agent python3 /opt/hermes/skills/pf-setup/scripts/setup.py --snapshot-at 2026-09-23T20:00:00Z
```

## Uninstalling

```bash
plow-agents revoke         # retire this credential's agent
docker compose down        # stop it, keep what it remembers
docker compose down -v     # stop it and forget everything
```

`revoke` with no argument retires the agent belonging to the credential file;
give it a line ID to retire whatever is on that line. Do it before you delete
the credential, or the line stays held by an agent you can no longer reach.

---

## What it stores, and what it doesn't

- `/var/lib/hermes/pf/config.json` — the slug you are watching, and the snapshot instant.
- `/var/lib/hermes/pf/state.json` — the last board read, and which countdown marks were spent.

Both survive rebuilds. Neither holds a credential, a chat id, or anything
identifying you. The agent reads one public endpoint, writes one JSON file, and
posts to your chat only when the comparison between them says something moved.

MIT licensed. The whole mechanism is four files and a cron — read them.
