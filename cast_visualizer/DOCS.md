# Cast Visualizer

A Music Assistant player that casts a projectM music visualizer to a Chromecast.

## Setup

1. In Music Assistant enable the **Squeezelite / SlimProto** provider.
2. Set **cast_name** to the friendly name of your Chromecast and start the add-on.
3. A player called **Visualizer** appears in Music Assistant. Play music on it.
4. Add the package and the blueprint from the repository to start the visualizer with the music:
   https://github.com/rdzjuanjo/ha-cast-visualizer#home-assistant-setup

Requires an Intel or AMD GPU (`/dev/dri/renderD128`). Video is encoded on the CPU (about 2–3 cores while
music plays).

## Options

- **cast_name** (required): Chromecast friendly name.
- **player_name**: name of the Music Assistant player.
- **host_ip**: IP the Chromecast uses to reach Home Assistant (auto-detected when empty).
- **port**: API and stream port (default 8099).
- **width / height / fps / video_bitrate**: video settings (854x480, 24 fps, 1800 kbit/s).
- **preset_duration**: seconds per visual.
- **silence_seconds**: stop after this much silence, resume on sound.
- **on_start_url / on_stop_url**: optional webhooks (POST) when it starts/stops.

Full documentation and troubleshooting: https://github.com/rdzjuanjo/ha-cast-visualizer
