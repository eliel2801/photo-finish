#!/usr/bin/env python3
"""Where you stand, right now, asked for.

The other half of this agent. `poll.py` interrupts; this one answers. It
prints and posts nothing: the owner is already in the conversation that asked,
so the agent relays what this prints as its own reply. A script that also
posted would double every answer.

Tokens appear here and not in the alerts on purpose. The hosts rank by installs
*and* token usage, but tokens move continuously -- alerting on them would mean
alerting always, which is the one thing this agent does not do. So they are a
number you can ask for, next to the one that interrupts you.
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


def thousands(n):
    return f"{n:,}"


def main():
    ap = argparse.ArgumentParser(description="Print the current standing.")
    ap.add_argument("--top", type=int, default=5, help="how many leaderboard rows to show (default 5)")
    ap.add_argument("--tokens", action="store_true", help="also fetch token usage (one extra request per row shown)")
    args = ap.parse_args()

    config = pf.load_config()
    agent_id = (config.get("agent_id") or "").strip()
    rows = pf.standings(pf.fetch_agents())
    me = pf.find(rows, agent_id) if agent_id else None
    left = pf.humanize_left(pf.hours_left(config))

    out = []

    if me:
        out.append(f"You are #{me['pos']} with {me['users']} installs. {left}.")
        target, need = pf.ahead_of(rows, me)
        if target:
            out.append(f"#{target['pos']} {target['name']} has {target['users']}; +{need} takes the spot.")
        else:
            out.append("Nobody is ahead of you on installs.")
        if args.tokens:
            mine = pf.total_tokens(pf.fetch_usage(agent_id))
            out.append(f"Your reported usage: {thousands(mine)} tokens.")
        # The two gates that disqualify quietly. Worth repeating until both
        # are true, because an unverified agent cannot win no matter what the
        # install count says.
        gates = []
        if not me["verified"]:
            gates.append("NOT verified yet -- ask the hosts on Discord")
        if not me["deployable"]:
            gates.append("not one-click deployable yet")
        if not me["has_video"]:
            gates.append("no video on your listing")
        if gates:
            out.append("Gates: " + "; ".join(gates) + ".")
    else:
        out.append(f"Spectator mode -- no agent of yours is being tracked. {left}.")

    out.append("")
    out.append(f"Top {args.top}:")
    for row in rows[: args.top]:
        mark = ">" if me and row["agent_id"] == me["agent_id"] else " "
        line = f"{mark} {row['pos']}. {row['name']} - {row['users']}"
        if args.tokens:
            line += f" - {thousands(pf.total_tokens(pf.fetch_usage(row['agent_id'])))} tok"
        out.append(line)

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
