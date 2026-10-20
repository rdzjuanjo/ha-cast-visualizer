"""HTTP API of the visualizer; also serves the HLS stream under /hls/.

GET /start /stop /status                  -> visualizer cast to the Chromecast (status: on/off)
GET /visual/next|previous|random|lock|unlock
GET /visual/current|summary|remove|favorite|unfavorite|only_favorites|all|mode
"""
import http.server
import threading
import urllib.parse

import visualizer
from config import load

opts = load()


class Handler(http.server.SimpleHTTPRequestHandler):
    # Debian guesses .ts as "text/vnd.trolltech.linguist"
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".ts": "video/mp2t", ".m3u8": "application/vnd.apple.mpegurl"}

    def __init__(self, *a, **k):
        super().__init__(*a, directory="/tmp", **k)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        actions = {"/start": lambda: visualizer.manual(True), "/stop": lambda: visualizer.manual(False),
                   "/status": lambda: "on" if visualizer.running() else "off",
                   **{f"/visual/{a}": (lambda a=a: visualizer.control(a)) for a in visualizer.CONTROL_ACTIONS}}
        if path in actions:
            try:
                msg, code = actions[path](), 200
            except Exception as e:
                msg, code = f"error: {e}", 500
            self.send_response(code)
            self.end_headers()
            self.wfile.write(str(msg).encode())
        elif path.startswith("/hls/"):
            try:
                super().do_GET()
            except (ConnectionResetError, BrokenPipeError):
                pass  # the Chromecast dropped the download (normal when switching apps)
        else:
            self.send_error(404)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=visualizer.watcher, daemon=True).start()
    threading.Thread(target=visualizer.watch_presets, daemon=True).start()
    print(f"Cast Visualizer on :{opts['port']} -> '{opts['cast_name']}' (stream from {opts['host_ip']})", flush=True)
    http.server.ThreadingHTTPServer(("0.0.0.0", opts["port"]), Handler).serve_forever()
