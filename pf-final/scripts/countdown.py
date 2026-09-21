#!/usr/bin/env python3
"""The last day, and the result.

Runs hourly and almost always does nothing. It speaks at four marks before the
snapshot -- 24h, 12h, 6h, 1h -- and once more after it, with the final board.

Why marks and not a countdown: an hourly countdown is a notification the owner
turns off on the second day, and a silent agent on the last day is an agent
that missed the only hours that mattered. Four interruptions across the final
day is the most this earns.

Each mark is recorded in state so a restart, a rebuild or a double-fired cron
cannot send it twice. `--force` replays one for testing and records nothing.
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

# Hours before the snapshot. Descending, and a mark fires when the clock is at
# or under it -- so an agent installed with 9h to go still gets the 6h and 1h
# marks, and never the ones it slept through.
MARKS = (24, 12, 6, 1)
FINAL = "final"


def board(rows, limit=3):
    return "\n".join(f"{r['pos']}. {r['name']} - {r['users']}" for r in rows[:limit])


def mark_message(hours, rows, me):
    """The message for one mark. `hours` is what gets rendered, so production
    passes the real time left -- to the minute, never rounded up to the mark --
    and --force passes the mark it is simulating. Recomputing the clock in here
    instead would make every forced replay print today's number and show the
    tester the one message they did not ask to see."""
    lines = [f"{pf.humanize_left(hours)} to the snapshot."]
    if me:
        target, need = pf.ahead_of(rows, me)
        lines.append(f"You: #{me['pos']}, {me['users']} installs.")
        if target:
            lines.append(f"+{need} would take #{target['pos']} from {target['name']} ({target['users']}).")
        else:
            lines.append("You are #1 on installs.")
        if not me["verified"]:
            lines.append("You are still NOT verified. Unverified cannot win -- go ask the hosts now.")
    lines.append("")
    lines.append(board(rows))
    return "\n".join(lines)


def final_message(rows, me):
    lines = ["Snapshot time. Final board:", "", board(rows, limit=5)]
    if me:
        lines.append("")
        lines.append(f"You finished #{me['pos']} with {me['users']} installs.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Speak at the final marks, and once at the snapshot.")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent; send nothing, record nothing")
    ap.add_argument("--force", type=str, help="replay one mark: 24, 12, 6, 1 or final")
    args = ap.parse_args()

    config = pf.load_config()
    agent_id = (config.get("agent_id") or "").strip()
    hours = pf.hours_left(config)
    state = pf.load_state()
    sent = set(state.get("marks_sent") or [])

    rows = pf.standings(pf.fetch_agents())
    me = pf.find(rows, agent_id) if agent_id else None

    if args.force:
        forced = args.force.strip()
        if forced == FINAL:
            text = final_message(rows, me)
        else:
            if not forced.isdigit() or int(forced) not in MARKS:
                allowed = ", ".join(str(m) for m in MARKS)
                sys.exit(f"--force takes one of: {allowed}, {FINAL} (got {args.force!r})")
            text = mark_message(float(forced), rows, me)
        # Always a dry run: --force exists to show a mark early, and a replay
        # that posted for real would spend an interruption the clock has not
        # earned yet.
        pf_chat.send(text, dry_run=True)
        return 0

    if hours <= 0:
        if FINAL in sent:
            print("final already sent")
            return 0
        pf_chat.send(final_message(rows, me), dry_run=args.dry_run)
        if not args.dry_run:
            state["marks_sent"] = sorted(sent | {FINAL})
            pf.save_state(state)
        return 0

    due = [m for m in MARKS if hours <= m and str(m) not in sent]
    if not due:
        print(f"nothing due ({pf.humanize_left(hours)})")
        return 0

    # Only the tightest mark that came due. Crossing two at once -- a restart
    # after a long gap -- is one message, not two.
    mark = min(due)
    pf_chat.send(mark_message(hours, rows, me), dry_run=args.dry_run)
    if not args.dry_run:
        # Every mark at or above this one is spent: they can never come due
        # again, and leaving them unrecorded would fire them all on the next tick.
        state["marks_sent"] = sorted(sent | {str(m) for m in MARKS if m >= mark})
        pf.save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
