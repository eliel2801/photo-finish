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
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-42cb36ed16f513e9c7461b3f355acec181c8a26d@sha256:7bb771761c075ef3736c4cc7bdc48402ce325ed35b5efb529b1b31ec7956fd40

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
