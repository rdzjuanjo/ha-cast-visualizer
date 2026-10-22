# Cast Visualizer for Home Assistant

A **Music Assistant player that shows a music visualizer on your TV through a Chromecast**.

Play music on the "Visualizer" player from Music Assistant (or from the Spotify app, via MA's Spotify Connect),
and your Chromecast shows [projectM](https://github.com/projectM-visualizer/projectm) visuals (MilkDrop presets)
reacting to the music in real time, while the sound plays through the TV.

![projectM visuals on a TV through a 2nd-gen Chromecast](docs/demo.gif)

## Features

- Appears in Music Assistant as a regular player (Squeezelite), so it works with every MA music source,
  groups, voice commands and the Spotify Connect plugin.
- Casts to any Google Cast device as an HLS stream, tuned for old Chromecasts (2nd/3rd gen).
- Pauses itself after a few seconds of silence (when you pause the music) and comes back when sound returns.
- If you cast something else to the Chromecast (Netflix, Jellyfin…) the visualizer steps aside to save CPU, and
  returns when the Chromecast is free again and the music is still playing.
- Visual control from Home Assistant: next / previous / random / keep this one, favorite, "never show this
  again", only favorites, and a sensor with the name of the current visual.
- Optional webhooks when it starts and stops, to turn on your TV, LEDs or anything else.

## How it works

```
Music Assistant ──► squeezelite ──► PulseAudio null sink ──► projectM (headless sway + Xwayland, GPU)
                                                     │                       │
                                                     └────── ffmpeg ◄─ wf-recorder
                                                              │ x264 + AAC, HLS (4 s segments)
                                                              ▼
                                         Chromecast  ◄── HTTP :8099/hls/stream.m3u8
```

More detail in [docs/how-it-works.md](docs/how-it-works.md).

## Requirements

- **Home Assistant** with **Music Assistant** (add-on or container) and its **Squeezelite** provider enabled.
- A **Chromecast** or other Google Cast device connected to your TV.
- An **x86-64 machine with an Intel or AMD GPU** (`/dev/dri/renderD128`) to run it. The video is encoded on the
  CPU: expect around 2–3 cores while music plays (tested on an i7-6500U). A Raspberry Pi is not recommended.

## Installation

### Home Assistant OS (add-on)

[![Add repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Frdzjuanjo%2Fha-cast-visualizer)

1. Click the button above (or *Settings → Add-ons → Add-on store → ⋮ → Repositories* and paste
   `https://github.com/rdzjuanjo/ha-cast-visualizer`).
2. Install **Cast Visualizer**, set `cast_name` to the name of your Chromecast and start it.

> The add-on is new: it has been tested with Docker, not yet on Home Assistant OS. Feedback is welcome.

### Docker (Home Assistant Container / Core)

```sh
git clone https://github.com/rdzjuanjo/ha-cast-visualizer
cd ha-cast-visualizer
cp docker-compose.example.yml docker-compose.yml   # set CAST_NAME
docker compose up -d --build
```

It needs `network_mode: host` (Google Cast and Squeezelite discovery) and `/dev/dri`.

## Configuration

| Option | Default | Description |
|---|---|---|
| `cast_name` | – | Friendly name of the Chromecast (as shown in the Google Home app). **Required.** |
| `player_name` | `Visualizer` | Name of the player in Music Assistant. |
| `host_ip` | auto | IP the Chromecast uses to reach this machine. Set it if auto-detection picks the wrong interface. |
| `port` | `8099` | HTTP API and stream port. |
| `width` / `height` / `fps` | `854` / `480` / `24` | Video size. Higher costs more CPU; old Chromecasts do best at 480p. |
| `video_bitrate` | `1800` | kbit/s. Old Chromecasts freeze with bitrate spikes, keep it modest. |
| `preset_duration` | `30` | Seconds per visual. |
| `silence_seconds` | `20` | Seconds of silence before the visualizer stops (it resumes on sound). |
| `on_start_url` / `on_stop_url` | – | Optional URLs that receive a `POST {"event": "start"/"stop"}`. |

With Docker, use the same names in upper case as environment variables (`CAST_NAME`, `PORT`, …).

## Home Assistant setup

1. **Package** – copy [`homeassistant/packages/cast_visualizer.yaml`](homeassistant/packages/cast_visualizer.yaml)
   to `/config/packages/` ([how to enable packages](https://www.home-assistant.io/docs/configuration/packages/))
   and restart Home Assistant. You get:
   - `switch.music_visualizer` – visualizer on/off
   - `switch.only_favorite_visuals`
   - `sensor.current_visual` – name of the visual on screen (+ favorite, mode, counts)
   - scripts: next, previous, random, keep this visual, let visuals change, favorite, never show again
2. **Blueprint** – start the visualizer automatically with the music:

   [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frdzjuanjo%2Fha-cast-visualizer%2Fblob%2Fmain%2Fhomeassistant%2Fblueprints%2Fautomation%2Fvisualizer_with_music.yaml)

   Choose the Music Assistant "Visualizer" player and, optionally, actions to run first (e.g. turn on the TV).
3. **Music Assistant** – see [docs/music-assistant.md](docs/music-assistant.md) (Squeezelite provider, Spotify
   Connect, volume).

### Webhooks example

```yaml
# automation: turn on the TV backlight when the visualizer starts
triggers:
  - trigger: webhook
    webhook_id: visualizer_started
    local_only: true
actions:
  - action: light.turn_on
    target: {entity_id: light.tv_backlight}
```

and set `on_start_url: http://<home-assistant-ip>:8123/api/webhook/visualizer_started`.

## HTTP API

| Endpoint | |
|---|---|
| `GET /start`, `/stop`, `/status` | visualizer on the Chromecast (`status` → `on`/`off`) |
| `GET /visual/next`, `previous`, `random`, `lock`, `unlock` | control projectM |
| `GET /visual/current`, `summary` | current visual (name / JSON) |
| `GET /visual/favorite`, `unfavorite`, `remove` | lists, stored in `/data/visualizer` |
| `GET /visual/only_favorites`, `all`, `mode` | show only favorites or everything |

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md): buffering, frozen Chromecast, black screen, high CPU,
Spotify Connect stuck on "connecting".

## Credits

[projectM](https://github.com/projectM-visualizer/projectm), [squeezelite](https://github.com/ralph-irving/squeezelite),
[Music Assistant](https://music-assistant.io), [sway](https://swaywm.org), [wf-recorder](https://github.com/ammen99/wf-recorder),
[FFmpeg](https://ffmpeg.org) and [PyChromecast](https://github.com/home-assistant-libs/pychromecast).

## License

[MIT](LICENSE). Contributions welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).
