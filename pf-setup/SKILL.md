---
name: pf-setup
description: First-run setup — find which row on the AI Worth Using Agent Index belongs to this owner, lock it in, register the two background crons, and confirm the snapshot deadline. Also handles spectator mode for an owner who has not published an agent, and changing the snapshot instant if the hosts confirm a different one. Use on the owner's first message, when they say their agent is not being tracked, when they publish a new agent, when they ask to watch a different agent, or when they ask what this agent is watching.
---

# Photo Finish — setup

One field decides everything: which row on the Index is theirs. The
leaderboard is public, so there is no account to link and no token to paste.

## The conversation

Ask one question: **what is your agent called on the Index?**

Then find it. Do not make the owner hunt for a slug — search on whatever they
gave you, including their own name, because the Index carries the builder.

```
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --search "receipt"
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --search "Tiago"
```

Show the matches, let them pick, then lock it in:

```
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --agent-id receiptsnap
```

The script verifies the slug against the live Index before writing it. A typo
here is an agent that polls forever about a row that does not exist, so it
refuses rather than guesses.

## If they have not published anything

Spectator mode is a real answer, not a deferral. Offer it in one line and move
on — plenty of people registered for this hackathon without shipping, and they
are still watching the race.

```
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --spectator
```

They get podium changes and the countdown. When they do publish, run setup
again with `--agent-id`.

## Then register the crons

Setup is not finished until the background jobs exist. Without them this agent
answers when spoken to and never speaks first, which is not what it is for.

```
python3 /opt/hermes/skills/pf-shared/scripts/register_crons.py
```

Idempotent: it reads what hermes already has and only creates what is missing.
Safe to run again whenever the owner is not sure.

## The snapshot instant

The default is `2026-09-22T20:00:00Z`, the end time on the Luma listing. The
body of that same listing says "September 23rd, 1pm PT" — one day later. They
disagree, and this agent does not guess: it counts down to the earlier one,
because a countdown that runs early costs a nudge and one that runs late costs
the prize.

If the hosts confirm the later instant, set it:

```
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --snapshot-at 2026-09-23T20:00:00Z
```

Tell the owner this discrepancy exists the first time you set them up. It is
the kind of thing they want to hear from you before it matters, not after.

## Confirming

```
python3 /opt/hermes/skills/pf-setup/scripts/setup.py --show
```

Close the setup by saying what happens next in one line: you will text them
when the board moves, and nothing when it does not.
