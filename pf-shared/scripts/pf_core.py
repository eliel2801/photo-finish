#!/usr/bin/env python3
"""The Agent Index, read and remembered.

Every other script in this agent goes through here. Three jobs:

1. Read the public Index (`/v1/agents`, `/v1/usage`). No credential: the
   leaderboard is open, which is why this agent needs nothing from its owner
   beyond which row is theirs.
2. Rank it. The Index returns rows in no promised order and the hosts rank by
   installs *and* token usage; the weighting is not published, so installs
   order the standings and tokens ride along as the second number. Anything
   that claims to know the official formula is inventing it.
3. Remember the last read, so the next one can say what CHANGED. That memory
   is the whole product -- a leaderboard anyone can refresh is not worth an
   agent, and a leaderboard that texts you only when it moved is.

State lives in PF_HOME, the agent's own home volume, and survives rebuilds.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

INDEX_BASE = (os.environ.get("PF_INDEX_BASE") or "https://agent-index-server.vercel.app").rstrip("/")
PF_HOME = pathlib.Path(os.environ.get("PF_HOME") or "/var/lib/hermes/pf")
CONFIG_PATH = PF_HOME / "config.json"
STATE_PATH = PF_HOME / "state.json"

# The hackathon's own clock. The Luma listing ends 2026-09-22T20:00Z while its
# body says "September 23rd, 1pm PT" -- one day apart, and nobody is served by
# this agent guessing. The earlier one is the default because a countdown that
# runs early costs a nudge and one that runs late costs the prize; `snapshot_at`
# in config.json overrides it the moment the hosts confirm which is real.
DEFAULT_SNAPSHOT = "2026-09-22T20:00:00Z"

USER_AGENT = "photo-finish agent (Agent Index watcher)"
TIMEOUT = 20


# --------------------------------------------------------------------------
# reading the Index
# --------------------------------------------------------------------------
def _get_json(path):
    req = urllib.request.Request(f"{INDEX_BASE}{path}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        if resp.status != 200:
            raise RuntimeError(f"{path} answered {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def fetch_agents():
    """Every published agent. Raises on a bad read -- a failed poll must stay
    silent and retry, never post a standing built from half an answer."""
    payload = _get_json("/v1/agents")
    agents = payload.get("agents") if isinstance(payload, dict) else payload
    if not isinstance(agents, list) or not agents:
        raise RuntimeError("/v1/agents returned no rows")
    return agents


def fetch_usage(agent_id):
    """One agent's daily token usage, by model. Returns [] when the Index has
    nothing for it -- a published agent that never reported is the normal case,
    not an error."""
    try:
        payload = _get_json(f"/v1/usage?agent_id={urllib.parse.quote(agent_id)}")
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, json.JSONDecodeError):
        return []
    return payload.get("daily") or []


def total_tokens(daily, since=None):
    """Input + output across every model. Cache reads are excluded: they are an
    artifact of how a runtime replays a prompt, not of anyone using the agent."""
    total = 0
    for day in daily:
        if since and (day.get("date") or "") < since:
            continue
        for model in day.get("models") or []:
            total += int(model.get("input") or 0) + int(model.get("output") or 0)
    return total


# --------------------------------------------------------------------------
# ranking
# --------------------------------------------------------------------------
def standings(agents):
    """Rows ordered by installs, with competition ranking: ties share a
    position and the next one skips (1, 2, 3, 3, 5). Name breaks a tie for
    display order only -- it never changes the shared position."""
    rows = sorted(agents, key=lambda a: (-int(a.get("users") or 0), (a.get("name") or "").lower()))
    out, last_users, last_pos = [], None, 0
    for i, a in enumerate(rows, start=1):
        users = int(a.get("users") or 0)
        pos = last_pos if users == last_users else i
        last_users, last_pos = users, pos
        out.append({
            "pos": pos,
            "agent_id": a.get("agent_id") or "",
            "name": a.get("name") or a.get("agent_id") or "?",
            "users": users,
            "verified": bool(a.get("blessed_at")),
            "deployable": bool(a.get("deployable_at")),
            "has_video": bool(a.get("has_video")),
            "images": int(a.get("image_count") or 0),
            "builder": ((a.get("builder") or {}).get("name") or ""),
        })
    return out


def find(rows, agent_id):
    for row in rows:
        if row["agent_id"] == agent_id:
            return row
    return None


def ahead_of(rows, me):
    """The nearest row strictly above mine, and how many installs would take
    its place. Returns (None, 0) when nobody is ahead."""
    better = [r for r in rows if r["users"] > me["users"]]
    if not better:
        return None, 0
    target = min(better, key=lambda r: r["users"])
    return target, target["users"] - me["users"] + 1


# --------------------------------------------------------------------------
# the clock
# --------------------------------------------------------------------------
def snapshot_at(config=None):
    raw = (config or {}).get("snapshot_at") or DEFAULT_SNAPSHOT
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def hours_left(config=None, now=None):
    now = now or datetime.now(timezone.utc)
    return (snapshot_at(config) - now).total_seconds() / 3600.0


def humanize_left(hours):
    """English, like every alert this agent sends: the hosts read these too."""
    if hours <= 0:
        return "the snapshot has passed"
    if hours < 1:
        return f"{int(hours * 60)} min left"
    if hours < 48:
        return f"{hours:.0f}h left"
    return f"{hours / 24:.1f} days left"


# --------------------------------------------------------------------------
# memory
# --------------------------------------------------------------------------
def _read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError) as exc:
        # A corrupt file is not an empty one. Reading it as empty would replay
        # every alert this agent has already sent.
        raise RuntimeError(f"{path} is unreadable ({exc}); fix or delete it before the next poll")


def _write(path, payload):
    """Atomic: a poll interrupted mid-write must not leave a half state that
    the next poll diffs against."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_config():
    return _read(CONFIG_PATH, {})


def save_config(cfg):
    _write(CONFIG_PATH, cfg)


def load_state():
    return _read(STATE_PATH, {})


def save_state(state):
    _write(STATE_PATH, state)


def snapshot_of(rows):
    """What the next poll compares against: position and installs per agent,
    plus who held the podium."""
    return {
        "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agents": {
            r["agent_id"]: {"pos": r["pos"], "users": r["users"], "name": r["name"]}
            for r in rows
        },
        "podium": [r["agent_id"] for r in rows[:3]],
    }


def remember(rows):
    """Store the snapshot WITHOUT discarding the keys other producers own.

    One state file, two writers. The poll rewrites the board every 20 minutes;
    the countdown records which of its four marks it has already spent. A
    blind save_state(snapshot_of(rows)) from the poll would erase `marks_sent`
    on the next tick and replay the whole final day's alerts, hour after hour,
    on the one day nobody wants to mute this agent.
    """
    state = load_state()
    state.update(snapshot_of(rows))
    save_state(state)
    return state
