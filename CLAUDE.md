# Cast Visualizer — notes for working on this repo

Home Assistant add-on (+ Docker image) that registers a Squeezelite player in Music Assistant and casts a
projectM visualizer to a Chromecast as HLS. Architecture: [docs/how-it-works.md](docs/how-it-works.md).

## Layout
- `cast_visualizer/` — the add-on: `config.yaml` (options/schema), `build.yaml`, `Dockerfile`,
  `rootfs/entrypoint.sh` (sway headless + PulseAudio null sink + squeezelite, then `app/server.py`).
- `cast_visualizer/app/` — `config.py` (options.json → env → defaults), `cast.py` (PyChromecast),
  `visualizer.py` (projectM, ffmpeg/HLS, preset lists, silence and other-app watchers), `hooks.py` (webhooks),
  `server.py` (HTTP API + `/hls/`).
- `homeassistant/` — package (command_line switches/sensor, rest_command, scripts) and blueprint.
- `docs/` — how it works, Music Assistant setup, troubleshooting.

## Conventions
- Everything in English (code, comments, docs, commits). Comments explain *why* (hardware quirks, Chromecast
  limits), as in the existing code.
- New settings go in `config.py` DEFAULTS **and** `cast_visualizer/config.yaml` (options + schema) **and** the
  README options table.
- Bump `version` in `cast_visualizer/config.yaml` and add a CHANGELOG entry (root and `cast_visualizer/`) for
  every user-facing change: HA OS only offers updates when the version changes.
- Keep the defaults tuned for old Chromecasts (854x480, 24 fps, 1800 kbit/s, 4 s segments, cast after 3).

## Testing
- `python3 -m py_compile cast_visualizer/app/*.py`; YAML: `yaml.safe_load` with a `!input` constructor for the
  blueprint.
- Build: `docker build -t cast-visualizer-test cast_visualizer`.
- Safe run (no Chromecast, no Music Assistant player registered):
  `docker run -d --init --name cv-test --network none --device /dev/dri:/dev/dri -e CAST_NAME=none -e PORT=8199 -v <tmpdir>:/data cast-visualizer-test`
  then call `/start` from inside the container: HLS segments must appear in `/tmp/hls` (854x480, 24 fps,
  h264 + aac) and the start must fail cleanly ("not found") leaving no projectM/ffmpeg/wf-recorder processes.
- A real cast test needs host networking and a Chromecast: use another `PORT` and `PLAYER_NAME` so it does not
  collide with an existing instance on the same machine, and remove the test player from Music Assistant after.
- Always remove test containers and images when done.
