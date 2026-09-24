#!/usr/bin/env python3
"""Read the Index, compare it with the last read, and speak only if it moved.

This is the whole agent. Everything else is setup or a nicety.

The discipline it keeps, and the reason anyone installs this: a run that finds
nothing sends nothing. The leaderboard is public and anyone can refresh it --
what nobody can do is stop refreshing it. This runs every 20 minutes so its
owner does not have to, and a run that texts "no change" is a run that teaches
its owner to mute the thread.

Two modes, decided by whether config.json names an agent:

  owner     -- config has `agent_id`. Speaks about that row: installs gained
               or lost, who overtook it, who it overtook, position moved.
  spectator -- config has none. Speaks only when the podium changes. Somebody
               who registered for the hackathon and has not published yet is
               still watching the race, and an agent that refuses to work for
               them is an agent they uninstall.

Messages are English on purpose: the Index, the hosts and most of the field
write English, and an alert the hosts cannot read is an alert wasted.

Exit codes: 0 whether or not it spoke. A failed read raises -- a poll that
cannot see the Index must retry on the next tick, never post a standing built
from half an answer.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "pf-shared", "scripts"),
)
import pf_chat  # noqa: E402
import pf_core as pf  # noqa: E402


def _plural(n, one, many):
    return one if abs(n) == 1 else many


def events_for_owner(prev_agents, rows, me):
    """What changed about MY row since the last poll, as short phrases.

    An empty list means silence. Every branch here has to earn its interruption
    -- if the reason would not make its owner look up from what they are doing,
    it does not belong.
    """
    events = []
    mine = prev_agents.get(me["agent_id"])

    if mine is None:
        # First sighting: either the first poll after publishing, or the first
        # poll after setup named a row that was already there. Either way the
        # baseline is what matters, not an alert.
        return events

    delta = me["users"] - int(mine.get("users") or 0)
    if delta > 0:
        events.append(
            f"+{delta} {_plural(delta, 'install', 'installs')}. You are on {me['users']}."
        )
    elif delta < 0:
        events.append(
            f"{delta} {_plural(delta, 'install', 'installs')} -- the Index now shows {me['users']}."
        )

    old_pos = int(mine.get("pos") or 0)
    if me["pos"] < old_pos:
        events.append(f"Up to #{me['pos']} (was #{old_pos}).")
    elif me["pos"] > old_pos:
        events.append(f"Down to #{me['pos']} (was #{old_pos}).")

    # Who crossed me. Compared on installs, not position: positions move when
    # a stranger three rows down gains one, and that is not news.
    my_old_users = int(mine.get("users") or 0)
    overtook, lost_to = [], []
    for row in rows:
        if row["agent_id"] == me["agent_id"]:
            continue
        before = prev_agents.get(row["agent_id"])
        if before is None:
            continue
        was_above = int(before.get("users") or 0) > my_old_users
        is_above = row["users"] > me["users"]
        # Passing means standing strictly above them now, not drawing level.
        # Competition ranking gives a tie a SHARED position, so "you passed X"
        # while both sit on #2 is a claim the board does not make. The gap
        # report already holds this line -- ahead_of() asks for the installs
        # that take a place, never the ones that tie it -- and these two have
        # to agree, because they arrive in the same message.
        is_below = row["users"] < me["users"]
        if is_above and not was_above:
            lost_to.append(row)
        elif was_above and is_below:
            overtook.append(row)

    for row in lost_to:
        events.append(f"{row['name']} passed you ({row['users']} vs your {me['users']}).")
    for row in overtook:
        events.append(f"You passed {row['name']}.")

    return events


def events_after_race(prev_agents, me):
    """Once the board is final, one thing is still news to a builder: somebody
    installed their agent, or an install went away. Rank moves are not -- they
    change no result, and texting them the morning after reads like a race
    that is still on."""
    mine = prev_agents.get(me["agent_id"])
    if mine is None:
        return []
    delta = me["users"] - int(mine.get("users") or 0)
    if delta > 0:
        return [f"+{delta} {_plural(delta, 'install', 'installs')}. You are on {me['users']}."]
    if delta < 0:
        return [f"{delta} {_plural(delta, 'install', 'installs')} -- the Index now shows {me['users']}."]
    return []


def events_for_spectator(prev, rows):
    """Spectator mode speaks for one reason: the podium changed."""
    before = prev.get("podium") or []
    now = [r["agent_id"] for r in rows[:3]]
    if not before or before == now:
        return []
    names = {r["agent_id"]: r["name"] for r in rows}
    podium = " / ".join(f"{i}. {names.get(a, a)}" for i, a in enumerate(now, 1))
    return [f"Podium changed: {podium}."]


def compose(events, rows, me, config):
    """One message. Never a digest -- the events, then one line of context."""
    lines = list(events)
    hours = pf.hours_left(config)
    if hours <= 0:
        # After the race there is no place to take and no clock to beat; the
        # clock line here once read "the snapshot has passed to the snapshot."
        if me:
            lines.append(f"Now #{me['pos']} of {len(rows)}. The race is over; installs still count.")
        return "\n".join(lines)
    clock = f"{pf.humanize_left(hours)} to the snapshot."

    if me:
        target, need = pf.ahead_of(rows, me)
        if target:
            lines.append(
                f"#{target['pos']} {target['name']} is on {target['users']}; "
                f"+{need} would take it. {clock}"
            )
        else:
            lines.append(f"You are #1 on installs. {clock}")
    else:
        lines.append(clock)

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Poll the Agent Index and alert only on change.")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent; send nothing, save nothing")
    ap.add_argument("--report", action="store_true", help="print the current standings and exit")
    args = ap.parse_args()

    config = pf.load_config()
    agent_id = (config.get("agent_id") or "").strip()
    hackathon, racing = pf.field(pf.fetch_agents(), agent_id, config)
    rows = pf.standings(racing)
    if not rows:
        raise RuntimeError(f"the Index has no rows in the {hackathon!r} hackathon")

    if args.report:
        for row in rows[:12]:
            mark = "*" if row["agent_id"] == agent_id else " "
            flag = "V" if row["verified"] else "-"
            print(f"{mark}{row['pos']:>3}. [{flag}] {row['name'][:28]:<28} {row['users']:>3}")
        return 0

    me = pf.find(rows, agent_id) if agent_id else None
    if agent_id and me is None:
        # Named a row the Index does not have. Loud, because every poll from
        # here on is dead and a silent agent looks identical to a working one.
        sys.exit(
            f"config.json names agent_id {agent_id!r}, which is not on the Index. "
            "Fix it with the pf-setup skill, or clear it for spectator mode."
        )

    prev = pf.load_state()
    prev_agents = prev.get("agents") or {}
    first_run = not prev_agents

    if first_run:
        # Nothing to diff against. Establish the baseline and stay quiet:
        # an agent whose first act is an unprompted alert has not earned one.
        # --dry-run promises to save nothing, and this is the one path where a
        # stranger meets it: INSTALL.md sends people here to try the agent
        # before installing it, on a home that has no state yet.
        if not args.dry_run:
            pf.remember(rows)
        where = f", you are #{me['pos']}" if me else ", spectator mode"
        verb = "would save baseline" if args.dry_run else "baseline saved"
        print(f"{verb}: {len(rows)} agents{where}")
        return 0

    if pf.hours_left(config) <= 0:
        # The board is final. An owner still hears about installs; a
        # spectator's podium can no longer change anything, so it hears nothing.
        events = events_after_race(prev_agents, me) if me else []
    else:
        events = events_for_owner(prev_agents, rows, me) if me else events_for_spectator(prev, rows)

    if not events:
        if not args.dry_run:
            pf.remember(rows)
        print("no change" + (f" (#{me['pos']}, {me['users']} installs)" if me else ""))
        return 0

    message = compose(events, rows, me, config)
    pf_chat.send(message, dry_run=args.dry_run)

    if not args.dry_run:
        # Only after the post. A crash between here and the send would replay
        # the alert next tick, which is the failure worth having.
        pf.remember(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
