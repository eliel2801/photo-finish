#!/usr/bin/env python3
"""The one way this agent reaches its owner.

A poll that finds nothing must say nothing, and Hermes' own `cron --deliver`
arm cannot do that: it relays every final response, no-ops included. So the
quiet-run producers here do not take it. They decide, and when there is
something to say they post it themselves, through this.

The credential comes from the container environment, which first boot
publishes from what the host dropped in. It is never read from a file the
agent can write, never passed in argv, and never followed across a redirect:
a 302 to another host with a bearer attached is how a token leaves the
building.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = 20


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(
            f"refusing to follow a {code} redirect to {newurl!r} while carrying the agent bearer"
        )


def require(name):
    value = (os.environ.get(name) or "").strip()
    if not value:
        sys.exit(
            f"{name} is unset or blank in this process's environment -- first boot "
            "publishes it there from the credential the host dropped in. Refusing "
            "to post: a message that silently goes nowhere is worse than a loud stop."
        )
    return value


def chat_endpoint():
    base = require("PLOW_API_BASE").rstrip("/")
    uid = require("PLOW_HOME_CHANNEL")
    token = require("PLOW_AGENT_TOKEN")
    return f"{base}/v1/chats/{uid}/messages", token


def send(text, dry_run=False):
    """Post one message to the owner. Returns the text that was sent."""
    text = (text or "").strip()
    if not text:
        raise ValueError("refusing to post an empty message")

    if dry_run:
        print("--- dry-run, nada foi enviado ---")
        print(text)
        print("--- fim ---")
        return text

    url, token = chat_endpoint()
    payload = json.dumps({"body": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "photo-finish agent",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            if resp.status not in (200, 201, 202, 204):
                raise RuntimeError(f"Plow Chat answered {resp.status}")
    except urllib.error.HTTPError as exc:
        # The body can carry the reason; the bearer never appears in it.
        raise RuntimeError(f"Plow Chat refused the post ({exc.code}): {exc.read()[:200]!r}") from exc
    return text
