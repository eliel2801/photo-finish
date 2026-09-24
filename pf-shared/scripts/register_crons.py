#!/usr/bin/env python3
"""Register this agent's two background jobs, idempotently.

`hermes cron` persists jobs to /var/lib/hermes/cron/jobs.json, and no rebuild
replays it -- so a rebuilt agent comes up having forgotten it was ever
watching anything, which looks exactly like a working agent that has nothing
to report. Keeping both rows in a versioned spec here means "set up my crons"
replays something reviewed instead of improvising two schedules from a
sentence.

Neither row takes `--deliver`. That arm relays every final response, no-ops
included, and both producers here are quiet by design: they run, they usually
find nothing, and they post for themselves through pf_chat when they do. A
--deliver on the watch row would text its owner "no change" seventy-two times
a day, which is the fastest way to be muted. Without it, Hermes still delivers
the final response to the originating chat, so each prompt ends by asking for
exactly [SILENT], the one reply it does not forward.

Idempotency reads hermes' own state file rather than parsing `hermes cron
list`: a name is a field there, not a substring of a human-readable listing.
The one absence that means "nothing is registered" is the file not existing.
Anything else -- unreadable, unexpected shape -- stops, because re-registering
on a bad read duplicates every job and there is no undo from inside a cron.

Runs INSIDE the container, where the hermes binary and that file live.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

HERMES = os.environ.get("PF_HERMES_BIN") or "/opt/hermes/bin/hermes"
JOBS_FILE = pathlib.Path(os.environ.get("PF_CRON_JOBS") or "/var/lib/hermes/cron/jobs.json")

# The spec. Two rows, both quiet, neither delivering.
JOBS = [
    {
        "name": "pf-watch",
        # Every 20 minutes. Fast enough that an install shows up while its
        # owner still remembers who they asked, slow enough that 66 rows of a
        # public endpoint is not a load anyone notices.
        "schedule": "*/20 * * * *",
        "skill": "pf-watch",
        "prompt": (
            "Run the pf-watch skill: poll the Agent Index and alert only if the standing moved. "
            "Post nothing yourself -- the skill's script decides and posts. "
            "Unless the script failed, your final response is exactly [SILENT]."
        ),
    },
    {
        "name": "pf-countdown",
        # Hourly, five past. Almost every run does nothing; the four that
        # matter are in the last 24 hours.
        "schedule": "5 * * * *",
        "skill": "pf-final",
        "prompt": (
            "Run the pf-final skill: fire a countdown mark if one is due, or the final board if the "
            "snapshot has passed. Post nothing yourself -- the skill's script decides and posts. "
            "Unless the script failed, your final response is exactly [SILENT]."
        ),
    },
]


def registered_jobs():
    """Names hermes already has. Absence of the file is the only empty."""
    try:
        raw = JOBS_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    payload = json.loads(raw)
    rows = payload.get("jobs") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{JOBS_FILE} is not a list of jobs; refusing to register over an unread schedule")
    out = {}
    for row in rows:
        name = (row or {}).get("name")
        if name:
            out[name] = row
    return out


def create(job, dry_run=False):
    argv = [HERMES, "cron", "create", job["schedule"], job["prompt"], "--name", job["name"]]
    if job.get("skill"):
        argv += ["--skill", job["skill"]]
    if dry_run:
        print("would run: " + " ".join(repr(a) if " " in a else a for a in argv))
        return
    subprocess.run(argv, check=True)


def main():
    ap = argparse.ArgumentParser(description="Register the Rank Alarm crons, idempotently.")
    ap.add_argument("--dry-run", action="store_true", help="print the commands; change nothing")
    args = ap.parse_args()

    if not args.dry_run and not (os.path.exists(HERMES) or shutil_which(HERMES)):
        raise SystemExit(f"{HERMES} not found -- run this inside the agent container")

    existing = registered_jobs()
    paused = []

    for job in JOBS:
        row = existing.get(job["name"])
        if row is not None:
            # Registered already. A paused row is left exactly as it is:
            # re-creating it duplicates the job, and resuming it silently
            # undoes a decision somebody made on purpose.
            if row.get("paused_at") or row.get("enabled") is False:
                paused.append(job["name"])
            print(f"already registered: {job['name']}")
            continue
        create(job, dry_run=args.dry_run)
        print(f"registered: {job['name']} ({job['schedule']})")

    if paused:
        print(
            "\nPAUSED and will never fire: "
            + ", ".join(paused)
            + f" -- resume with: {HERMES} cron resume <name>"
        )
    return 0


def shutil_which(binary):
    import shutil

    return shutil.which(binary)


if __name__ == "__main__":
    raise SystemExit(main())
