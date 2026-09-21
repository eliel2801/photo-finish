# Photo Finish — a Hermes agent that watches the Agent Index leaderboard.
#
# There is no code of this agent's own below: the runtime, the boot, the chat
# plugin and the Agent Index usage reporter all arrive with the base image.
# What this file adds is a persona and five skill directories — the tracked
# files this repo owns.
#
# The tag is an immutable `base-<sha>` naming one commit of the base's source
# repo, plow-pbc/plow-hermes-agent, pinned by digest. It is never moved: every
# tenant boots this exact filesystem while holding their own Plow credential,
# so a floating tag would substitute code underneath them.
#
# To move to a newer base, read plow-pbc/plow-hermes-agent, take the tag AND
# its digest, bump both here, and rebuild. Never bump the tag alone.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-204252baa28652563c048a4f8ac5d95d30ee396d@sha256:0ed0e0380c55c37792e7c3c1af2a5e8ca4b20e5437272ff927d1199fedb3997f

# Identity. plow-init writes the home's SOUL.md on every boot as the base
# persona followed by this file, so nothing is COPYed to
# /var/lib/hermes/SOUL.md — that path is overwritten at boot. The base already
# carries the voice, no-fabrication and untrusted-content rules; this file adds
# only what is specific to watching a leaderboard.
COPY --chmod=0644 runtime/persona.md /opt/hermes/plow-seed/persona.md

# MIT, and the hackathon requires it to be in the image as well as the repo.
COPY LICENSE /usr/share/doc/photo-finish/

# Shipped at /opt/hermes/skills, outside every home, so a bind-mounted home
# still receives them and an image update still reaches an uncustomised skill —
# both via the base runtime's reconcile into whichever home this gets.
COPY pf-shared/   /opt/hermes/skills/pf-shared/
COPY pf-setup/    /opt/hermes/skills/pf-setup/
COPY pf-watch/    /opt/hermes/skills/pf-watch/
COPY pf-standing/ /opt/hermes/skills/pf-standing/
COPY pf-final/    /opt/hermes/skills/pf-final/

# Normalize whatever modes the checkout carried. A Windows checkout hands over
# files with no executable bit and a blanket 0644 would leave every script
# unrunnable, so scripts and directories are set explicitly. Scoped to this
# agent's own directories: the skills root and the base's seed skills belong to
# the base, and recursing over them would reset modes this image does not own.
RUN set -eux; \
    find /opt/hermes/skills/pf-* -type d -exec chmod 0755 {} +; \
    find /opt/hermes/skills/pf-* -type f -name '*.py' -exec chmod 0755 {} +; \
    find /opt/hermes/skills/pf-* -type f ! -name '*.py' -exec chmod 0644 {} +

# A build that shipped a broken script would only fail at 07:05 on the last
# day, in front of nobody. Compiling every script here turns that into a build
# failure, which is the failure worth having.
RUN python3 -m compileall -q /opt/hermes/skills/pf-shared /opt/hermes/skills/pf-setup \
    /opt/hermes/skills/pf-watch /opt/hermes/skills/pf-standing /opt/hermes/skills/pf-final

# ---------------------------------------------------------------------------
# The Agent Index usage reporter.
#
# The base image does NOT carry this. Measured on the pinned base above:
# there is no /opt/plow, no agent-index-client.py and no agent-index service
# in /etc/s6-overlay/s6-rc.d. plow-init publishes AGENT_ID into the container
# environment and nothing consumes it. The Index's own "publish an agent"
# instructions say so in step 3 -- "bake the reporter into your image with
# AGENT_ID=<your-agent-id>, copy the agent-index service from the example" --
# and this is that copy.
#
# Without it this agent runs perfectly, answers every text, and scores
# nothing: no registration, no install ever counted, and zero tokens on a
# board that ranks by installs AND usage. It is the failure this repo's README
# has always described and, until now, shipped.
#
# Fetched at build from the commit vendor/client.pin names and checked against
# the hash beside it. Fetched rather than committed because
# plow-pbc/agent-index-client owns that file; pinned rather than tracked from a
# branch because this runs inside an agent holding a live credential, and a
# moving reference would substitute unreviewed code under it. The checksum is
# the second half: a sha in a URL is only as good as the host serving it.
COPY vendor/client.pin /opt/plow/agent-index-client.pin
RUN set -eu; \
    sha="$(sed -n 's/^sha=//p' /opt/plow/agent-index-client.pin)"; \
    want="$(sed -n 's/^sha256=//p' /opt/plow/agent-index-client.pin)"; \
    path="$(sed -n 's/^path=//p' /opt/plow/agent-index-client.pin)"; \
    curl -fsS --max-time 60 -o /opt/plow/agent-index-client.py \
      "https://raw.githubusercontent.com/plow-pbc/agent-index-client/${sha}/${path}"; \
    got="$(sha256sum /opt/plow/agent-index-client.py | cut -d' ' -f1)"; \
    [ "$got" = "$want" ] || { echo "agent-index client is $got, pin says $want" >&2; exit 1; }; \
    chmod 0644 /opt/plow/agent-index-client.py

# The service itself, into the supervision tree beside the base's own five.
# COPY merges: user/contents.d keeps dashboard, hermes-gateway, home-guard,
# main-hermes and plow-init, and gains agent-index.
COPY image/s6-overlay/ /etc/s6-overlay/

# A Windows checkout carries no executable bit, and an s6 `run` without one is
# a service that never starts -- silently, which is the only way this failure
# ever presents.
RUN chmod 0755 /etc/s6-overlay/s6-rc.d/agent-index/run

# Which agent this is, baked in. plow-init's Credentials model reads the
# process environment and NOTHING else (settings_customise_sources returns
# env_settings alone), so AGENT_ID has to already be in the container's
# environment when it boots. Locally that came from plow-credentials via
# compose's env_file. On Plow's cloud a direct image reference -- not a
# promoted `exe:` slug -- arrives with no AGENT_ID at all, the reporter logs
# "standing down", and the agent reports zero tokens while running perfectly.
# Measured: the cloud instance sat at the same total for seven minutes after
# its first turn. The Index's own publish instructions say to bake it in.
#
# It is the same value every install must keep (INSTALL.md, step 3), so baking
# it also removes the one variable an installer could get wrong.
ENV AGENT_ID=photo-finish
