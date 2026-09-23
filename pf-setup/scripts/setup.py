#!/usr/bin/env python3
"""Name the row on the Index that belongs to this owner, once.

Everything this agent needs fits in one field. There is no account to link, no
token to paste, no OAuth dance: the leaderboard is public, so the only thing
the agent cannot work out for itself is which of the rows is yours.

Three ways to answer, in the order a real conversation goes:

  --search NAME    the owner half-remembers what they called it, or who built
                   it. Prints candidates; picks nothing.
  --agent-id SLUG  the owner knows the slug. Verified against the live Index
                   before it is written, because a typo here is an agent that
                   polls forever about a row that does not exist.
  --spectator      the owner has not published anything. A real answer, not a
                   deferral -- spectator mode follows the podium.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "pf-shared", "scripts"),
)
import pf_core as pf  # noqa: E402


def search(rows, term):
    term = term.lower().strip()
    hits = [
        r for r in rows
        if term in r["name"].lower() or term in r["agent_id"].lower() or term in r["builder"].lower()
    ]
    if not hits:
        print(f"Nothing on the Index matches {term!r}. Try part of the agent name or the builder name.")
        return 1
    print(f"{len(hits)} match(es):")
    for row in hits[:15]:
        unit = "install " if row["users"] == 1 else "installs"
        print(f"  {row['agent_id']:<26} {row['name'][:26]:<26} {row['users']:>3} {unit}   {row['builder']}")
    print("\nRun setup again with --agent-id <slug> to lock one in.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Tell Rank Alarm which row is yours.")
    ap.add_argument("--agent-id", help="the slug of your agent on the Index")
    ap.add_argument("--search", help="find your agent_id by agent name or builder name")
    ap.add_argument("--spectator", action="store_true", help="follow the race without an agent of your own")
    ap.add_argument("--snapshot-at", help="override the snapshot instant, ISO-8601 UTC (e.g. 2026-09-23T20:00:00Z)")
    ap.add_argument("--show", action="store_true", help="print the current config and exit")
    args = ap.parse_args()

    config = pf.load_config()

    if args.show:
        print(f"agent_id:    {config.get('agent_id') or '(spectator)'}")
        print(f"snapshot_at: {config.get('snapshot_at') or pf.DEFAULT_SNAPSHOT + '  (default)'}")
        print(f"{pf.humanize_left(pf.hours_left(config))}")
        return 0

    if args.snapshot_at:
        # Parsed before it is stored: a bad instant here silences the countdown
        # for good, and it would look like the countdown simply never fired.
        pf.snapshot_at({"snapshot_at": args.snapshot_at})
        config["snapshot_at"] = args.snapshot_at
        pf.save_config(config)
        print(f"snapshot set to {args.snapshot_at} ({pf.humanize_left(pf.hours_left(config))}).")
        if not (args.agent_id or args.search or args.spectator):
            return 0

    if args.search:
        return search(pf.standings(pf.fetch_agents()), args.search)

    if args.spectator:
        config.pop("agent_id", None)
        pf.save_config(config)
        # The baseline belongs to the mode that made it. Dropping it here means
        # the next poll re-reads the board rather than diffing owner-shaped
        # memory against a spectator-shaped question.
        pf.save_state({})
        print("Spectator mode. I will speak when the podium changes.")
        return 0

    if not args.agent_id:
        ap.error("give me --agent-id, or --search to find it, or --spectator")

    rows = pf.standings(pf.fetch_agents())
    me = pf.find(rows, args.agent_id.strip())
    if me is None:
        print(f"{args.agent_id!r} is not on the Index right now.")
        print("If you just published, give it a minute. Otherwise try --search.")
        return 1

    config["agent_id"] = me["agent_id"]
    pf.save_config(config)
    pf.save_state({})
    unit = "install" if me["users"] == 1 else "installs"
    print(f"Locked in: {me['name']} ({me['agent_id']}) -- #{me['pos']}, {me['users']} {unit}.")
    print(f"{pf.humanize_left(pf.hours_left(config))} to the snapshot. I will text you when it moves.")
    if not me["verified"]:
        print("Heads up: this row is NOT verified yet, so it cannot win. Ask the hosts on Discord.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
