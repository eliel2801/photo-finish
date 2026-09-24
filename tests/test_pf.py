#!/usr/bin/env python3
"""Offline tests for the parts that decide whether this agent is worth keeping.

No network, no container, no credential: every case here is a hand-built board
fed straight to the ranking and the diff. Run it anywhere:

    python3 tests/test_pf.py

What is covered is what breaks quietly. A wrong install count is loud and
somebody reports it; an alert that fires twice, or a silence that should have
been an alert, is neither -- the owner just drifts away from the thread.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
os.environ.setdefault("PF_HOME", tempfile.mkdtemp(prefix="pf-test-"))
sys.path.insert(0, str(ROOT / "pf-shared" / "scripts"))
sys.path.insert(0, str(ROOT / "pf-watch" / "scripts"))

import pf_core as pf  # noqa: E402
import poll  # noqa: E402

FAILURES = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}\n         got:  {got!r}\n         want: {want!r}")
        FAILURES.append(name)


def board(*pairs):
    """(agent_id, users) -> the shape /v1/agents returns."""
    return [
        {"agent_id": a, "name": a.title(), "users": u, "blessed_at": "2026-09-10T00:00:00Z",
         "hackathon": "hermes"}
        for a, u in pairs
    ]


# --------------------------------------------------------------------------
print("\nranking")
# --------------------------------------------------------------------------
rows = pf.standings(board(("a", 16), ("b", 5), ("c", 2), ("d", 2), ("e", 2), ("f", 0)))
check("leader is #1", rows[0]["pos"], 1)
check("runner-up is #2", rows[1]["pos"], 2)
# Competition ranking: three agents tied on 2 installs are all #3, and the next
# row is #6. This is what the site shows, and an agent that reported #4 and #5
# to two of those three would be reporting a position nobody else can see.
check("three-way tie all share #3", [r["pos"] for r in rows[2:5]], [3, 3, 3])
check("position after a three-way tie skips to #6", rows[5]["pos"], 6)

me = pf.find(rows, "c")
target, need = pf.ahead_of(rows, me)
check("nearest ahead of a tied row is the row above the tie", target["agent_id"], "b")
# +4 = reach 5 and add one. Tying does not take a position.
check("installs needed passes, not ties", need, 4)

leader = pf.find(rows, "a")
check("nobody ahead of the leader", pf.ahead_of(rows, leader)[0], None)

# --------------------------------------------------------------------------
print("\ndiff: what earns an interruption")
# --------------------------------------------------------------------------
before = pf.snapshot_of(pf.standings(board(("a", 16), ("b", 5), ("me", 3), ("c", 2))))["agents"]

same = pf.standings(board(("a", 16), ("b", 5), ("me", 3), ("c", 2)))
check("nothing moved -> silence", poll.events_for_owner(before, same, pf.find(same, "me")), [])

# A stranger three rows down gaining one install shifts nobody's standing and
# must not produce a message.
noise = pf.standings(board(("a", 16), ("b", 5), ("me", 3), ("c", 3)))
evts = poll.events_for_owner(before, noise, pf.find(noise, "me"))
check("a tie forming below me is not news", evts, [])

gained = pf.standings(board(("a", 16), ("b", 5), ("me", 4), ("c", 2)))
evts = poll.events_for_owner(before, gained, pf.find(gained, "me"))
check("one install reads singular", evts[0], "+1 install. You are on 4.")

gained2 = pf.standings(board(("a", 16), ("b", 5), ("me", 6), ("c", 2)))
evts = poll.events_for_owner(before, gained2, pf.find(gained2, "me"))
check("passing someone says so", "You passed B." in evts, True)
check("and reports the position", "Up to #2 (was #3)." in evts, True)

# Drawing level is not passing. Competition ranking gives both rows the SAME
# position, so an alert claiming a pass describes a board nobody else can see --
# and it would contradict the gap line sitting right under it in the same
# message, which counts the installs that take a place, not the ones that tie.
drew = pf.standings(board(("a", 16), ("b", 5), ("me", 5), ("c", 2)))
evts = poll.events_for_owner(before, drew, pf.find(drew, "me"))
check("tying someone is not passing them", [e for e in evts if "passed" in e], [])
check("but the installs still get reported", evts[0], "+2 installs. You are on 5.")
check("a tie really does share the position",
      pf.find(drew, "me")["pos"], pf.find(drew, "b")["pos"])

# The row above draws level with me by losing ground: same shared position,
# same silence about passing.
drawn_on = pf.standings(board(("a", 16), ("b", 3), ("me", 3), ("c", 2)))
check("being drawn level with is not being passed",
      [e for e in poll.events_for_owner(before, drawn_on, pf.find(drawn_on, "me")) if "passed" in e],
      [])

passed = pf.standings(board(("a", 16), ("b", 5), ("me", 3), ("c", 4)))
evts = poll.events_for_owner(passed and before, passed, pf.find(passed, "me"))
check("being overtaken says who", "C passed you (4 vs your 3)." in evts, True)

lost = pf.standings(board(("a", 16), ("b", 5), ("me", 2), ("c", 2)))
evts = poll.events_for_owner(before, lost, pf.find(lost, "me"))
check("a lost install reads singular too", evts[0], "-1 install -- the Index now shows 2.")

# Just published, or setup just pointed at a row the last snapshot predates.
# There is nothing to compare against, and an agent whose first unprompted act
# is an alert about a delta it invented has not earned the interruption.
fresh = pf.standings(board(("a", 16), ("b", 5), ("me", 3), ("newbie", 1)))
check("a row we have never seen is a baseline, not an alert",
      poll.events_for_owner(before, fresh, pf.find(fresh, "newbie")), [])

# --------------------------------------------------------------------------
print("\nthe listing fields a builder can still fix")
# --------------------------------------------------------------------------
# Unanimous among the rows that qualify and roughly a third of those below, so
# these are entry fees rather than differentiators -- and standing.py reads them
# straight off the row. A missing field must read as missing, not as a blank
# that quietly passes the gate.
rich = pf.standings([
    {"agent_id": "full", "name": "Full", "users": 4, "blessed_at": "2026-09-01",
     "deployable_at": "2026-09-01", "has_video": True,
     "install_url": " https://example.test/INSTALL.md ", "install_success": 100},
    {"agent_id": "bare", "name": "Bare", "users": 2},
])
full, bare = pf.find(rich, "full"), pf.find(rich, "bare")
check("install_url is carried and stripped", full["install_url"], "https://example.test/INSTALL.md")
check("a listing with no install link reads empty", bare["install_url"], "")
check("install_success rides along", full["install_success"], 100)
check("an unreported success rate is None, not zero", bare["install_success"], None)
check("gates stay false when the fields are absent",
      [bare["verified"], bare["deployable"], bare["has_video"]], [False, False, False])

# --------------------------------------------------------------------------
print("\ndiff: spectator mode")
# --------------------------------------------------------------------------
prev = pf.snapshot_of(pf.standings(board(("a", 16), ("b", 5), ("c", 3))))
check("same podium -> silence",
      poll.events_for_spectator(prev, pf.standings(board(("a", 16), ("b", 5), ("c", 3)))), [])
moved = pf.standings(board(("a", 16), ("c", 9), ("b", 5)))
check("podium change speaks once", len(poll.events_for_spectator(prev, moved)), 1)

# --------------------------------------------------------------------------
print("\nstate: two writers, one file")
# --------------------------------------------------------------------------
# The bug this guards: the poll rewrites the board every 20 minutes and the
# countdown records its spent marks in the same file. A blind replace erases
# marks_sent and replays the whole final day's alerts, hour after hour.
pf.save_state({"marks_sent": ["24", "12"]})
pf.remember(pf.standings(board(("a", 16), ("me", 3))))
kept = pf.load_state()
check("remember() keeps another writer's keys", kept.get("marks_sent"), ["24", "12"])
check("remember() still stores the board", sorted(kept["agents"]), ["a", "me"])

# --------------------------------------------------------------------------
print("\nthe clock")
# --------------------------------------------------------------------------
from datetime import datetime, timezone  # noqa: E402

cfg = {"snapshot_at": "2026-09-22T20:00:00Z"}
now = datetime(2026, 9, 22, 14, 0, tzinfo=timezone.utc)
check("hours to the snapshot", round(pf.hours_left(cfg, now)), 6)
# Counting to the wrong day does not cost a nudge, it costs the last day: the
# countdown posts the final board, records it, and prints "final already sent"
# forever after. The hosts' own card says "final ranking Sep 23".
check("a day early would already have declared the race over",
      pf.hours_left({}, datetime(2026, 9, 22, 21, 0, tzinfo=timezone.utc)) > 0, True)
check("under an hour reads in minutes", pf.humanize_left(0.5), "30 min left")
check("a passed snapshot says so", pf.humanize_left(-3), "the snapshot has passed")
check("config overrides the default", pf.snapshot_at(cfg).day, 22)
check("no config falls back to the date the hosts publish",
      pf.snapshot_at({}).isoformat(), "2026-09-23T20:00:00+00:00")


# --------------------------------------------------------------------------
print("\nthe field")
# --------------------------------------------------------------------------
# The Index lists every hackathon on one board. On 2026-09-24 that put this
# agent at #24 counting OpenClaw rows it was never racing.
mixed = board(("a", 16), ("me", 1)) + [
    {"agent_id": "claw", "name": "Claw", "users": 9, "hackathon": "openclaw"},
    {"agent_id": "loose", "name": "Loose", "users": 5},
]
hack, racing = pf.field(mixed, "me")
check("my row's hackathon names the field", hack, "hermes")
check("other hackathons are not my rivals", sorted(r["agent_id"] for r in racing), ["a", "me"])
check("a spectator takes config's hackathon",
      [r["agent_id"] for r in pf.field(mixed, "", {"hackathon": "openclaw"})[1]], ["claw"])
check("and falls back to hermes", pf.field(mixed, "")[0], "hermes")


# --------------------------------------------------------------------------
print("\nafter the snapshot")
# --------------------------------------------------------------------------
# The live agent texted "the snapshot has passed to the snapshot." and kept
# reporting rank drops the morning after the board froze.
over = {"snapshot_at": "2000-01-01T00:00:00Z"}
late = pf.standings(board(("a", 16), ("b", 2), ("me", 1)))
msg = poll.compose(["+1 install. You are on 1."], late, pf.find(late, "me"), over)
check("after the race the context line has no clock", msg.splitlines()[-1],
      "Now #3 of 3. The race is over; installs still count.")
check("a live clock still counts down",
      poll.compose([], late, None, {"snapshot_at": "2999-01-01T00:00:00Z"}).endswith("left to the snapshot."), True)

pf.save_config({"agent_id": "me", **over})
if pf.STATE_PATH.exists():
    pf.STATE_PATH.unlink()
_fetch, _send = pf.fetch_agents, poll.pf_chat.send
sent = []
poll.pf_chat.send = lambda text, dry_run=False: sent.append(text)
sys.argv = ["poll.py"]


def run_poll(*pairs):
    pf.fetch_agents = lambda: board(*pairs)
    poll.main()


try:
    run_poll(("a", 16), ("b", 2), ("me", 1))                 # baseline
    run_poll(("a", 16), ("b", 2), ("c", 3), ("me", 1))       # a rival arrives, I drop a place
    check("a rank drop after the race is silent", sent, [])
    run_poll(("a", 16), ("b", 2), ("c", 3), ("me", 2))       # somebody installs me
    check("an install after the race still speaks",
          sent[0].splitlines()[0] if sent else None, "+1 install. You are on 2.")
finally:
    pf.fetch_agents, poll.pf_chat.send = _fetch, _send

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    raise SystemExit(1)
print("all green")
