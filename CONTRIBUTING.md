# Contributing

Thanks for wanting to help! This started as a one-person setup (an i7-6500U laptop and a 2nd-gen Chromecast),
so reports from other hardware and other Home Assistant installs are the most valuable thing right now.

## Ways to help

- **Try it and report back**, even if it just works: open an issue or a Discussion with your hardware,
  Chromecast model and install type. Look for the [`help wanted`](../../issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22)
  and [`good first issue`](../../issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) labels.
- **Bugs**: use the bug report template and attach the add-on / container log.
- **Ideas and questions**: [Discussions](../../discussions) are better than issues for open-ended topics.

## Project layout

- `cast_visualizer/` — the add-on (and Docker image): `config.yaml`, `Dockerfile`, `rootfs/entrypoint.sh`.
- `cast_visualizer/app/` — the Python app: `config.py`, `cast.py`, `visualizer.py`, `hooks.py`, `server.py`.
- `homeassistant/` — package and blueprint.
- `docs/` — how it works, Music Assistant setup, troubleshooting.

[docs/how-it-works.md](docs/how-it-works.md) explains the pipeline and why each piece is there.

## Development

```sh
docker build -t cast-visualizer-test cast_visualizer
python3 -m py_compile cast_visualizer/app/*.py
```

Safe run without a Chromecast and without registering a player in Music Assistant:

```sh
docker run -d --init --name cv-test --network none --device /dev/dri:/dev/dri \
  -e CAST_NAME=none -e PORT=8199 -v "$(mktemp -d)":/data cast-visualizer-test
```

`/start` should produce HLS segments in `/tmp/hls` inside the container and then fail cleanly ("not found").

For a real test you need host networking and a Chromecast. If another instance runs on the same machine, use a
different `PORT` and `PLAYER_NAME`, and remove the test player from Music Assistant afterwards. Without the
blueprint the visualizer does not start by itself: call `http://<host>:<port>/start` once music is playing.

## Pull requests

- Keep code, comments, docs and commits in English. Comments should explain *why* (hardware quirks, Chromecast
  limits), like the existing ones.
- A new option goes in `config.py` `DEFAULTS`, in `cast_visualizer/config.yaml` (options **and** schema) and in
  the README options table.
- For user-facing changes, bump `version` in `cast_visualizer/config.yaml` and add an entry to both
  `CHANGELOG.md` files: Home Assistant OS only offers an update when the version changes.
- Keep the defaults safe for old Chromecasts (854x480, 24 fps, 1800 kbit/s, 4 s segments).
- Say in the PR what you tested it on (hardware, Chromecast model, HA install type).
