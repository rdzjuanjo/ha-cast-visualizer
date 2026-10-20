"""Settings: add-on options (/data/options.json) or environment variables (Docker), in that order.

`python3 config.py --shell` prints them as shell exports for the entrypoint.
"""
import json
import os
import socket
import sys

DEFAULTS = {
    "cast_name": "",              # friendly name of the Chromecast / Google Cast device
    "player_name": "Visualizer",  # name of the player that appears in Music Assistant
    "host_ip": "",                # IP the Chromecast uses to reach this machine (auto-detected if empty)
    "port": 8099,                 # HTTP API + HLS stream
    "width": 854,
    "height": 480,
    "fps": 24,
    "video_bitrate": 1800,        # kbit/s; old Chromecasts choke on bitrate spikes
    "preset_duration": 30,        # seconds per visual
    "silence_seconds": 20,        # stop the visualizer after this much silence (pause), resume on sound
    "on_start_url": "",           # optional webhook (POST) when the visualizer starts
    "on_stop_url": "",            # optional webhook (POST) when the visualizer stops
}

OPTIONS_FILE = "/data/options.json"


def detect_ip():
    """IP of the interface used to reach the LAN (no packet is sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def load():
    opts = dict(DEFAULTS)
    if os.path.exists(OPTIONS_FILE):
        opts.update({k: v for k, v in json.load(open(OPTIONS_FILE)).items() if v not in (None, "")})
    for key, default in DEFAULTS.items():
        value = os.environ.get(key.upper())
        if value not in (None, ""):
            opts[key] = type(default)(value)
    if not opts["host_ip"]:
        opts["host_ip"] = detect_ip()
    return opts


if __name__ == "__main__" and "--shell" in sys.argv:
    import shlex
    for key, value in load().items():
        print(f"export CV_{key.upper()}={shlex.quote(str(value))}")
