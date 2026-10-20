"""Optional webhooks fired when the visualizer starts or stops (e.g. to turn on LEDs or a TV from Home Assistant)."""
import json
import threading
import urllib.request

from config import load

_opts = load()


def fire(event):
    url = _opts.get(f"on_{event}_url")
    if not url:
        return

    def run():
        try:
            req = urllib.request.Request(url, json.dumps({"event": event}).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).read()
        except Exception as e:
            print(f"hook {event}: {e}", flush=True)

    threading.Thread(target=run, daemon=True).start()
