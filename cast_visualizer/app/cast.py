"""Persistent connection to the Chromecast and casting of the HLS stream."""
import time

import pychromecast

from config import load

_opts = load()
STREAM_PATH = "/hls/stream.m3u8"
_cast = {}


def device():
    """Connected Chromecast. Discovery must stay alive while connecting, so the browser is kept."""
    cc = _cast.get("cc")
    if cc is not None and cc.socket_client.is_connected:
        return cc
    if not _opts["cast_name"]:
        raise RuntimeError("cast_name is not set")
    if _cast.get("browser"):
        _cast["browser"].stop_discovery()
    ccs, browser = pychromecast.get_listed_chromecasts(friendly_names=[_opts["cast_name"]], timeout=10)
    if not ccs:
        browser.stop_discovery()
        raise RuntimeError(f"Chromecast '{_opts['cast_name']}' not found")
    cc = ccs[0]
    cc.wait(timeout=20)
    _cast.update(cc=cc, browser=browser)
    return cc


def forget():
    cc, browser = _cast.pop("cc", None), _cast.pop("browser", None)
    for f in (lambda: cc.disconnect(timeout=5), lambda: browser.stop_discovery()):
        try:
            f()
        except Exception:
            pass


def cast_stream():
    """Send the stream to the Chromecast; if the saved connection died (device rebooted), reconnect and retry once."""
    for attempt in (1, 2):
        try:
            cc = device()
            # if another app is open (Jellyfin, Spotify...) the stream would play inside it and not close with the
            # visualizer: quit it and use the plain Default Media Receiver (lighter on old Chromecasts)
            if cc.app_id not in (None, pychromecast.APP_MEDIA_RECEIVER, pychromecast.APP_BACKDROP):
                cc.quit_app()
                for _ in range(20):
                    if cc.app_id in (None, pychromecast.APP_BACKDROP):
                        break
                    time.sleep(0.5)
            mc = cc.media_controller
            mc.play_media(f"http://{_opts['host_ip']}:{_opts['port']}{STREAM_PATH}", "application/x-mpegURL",
                          title="Visualizer", stream_type="LIVE")
            mc.block_until_active(timeout=15)
            return
        except Exception as e:
            print(f"cast (attempt {attempt}):", e, flush=True)
            forget()
            if attempt == 2:
                raise


def state():
    """'ours' (the visualizer), 'free' (idle screen), 'other' (any other app) or None if unreachable."""
    try:
        cc = _cast.get("cc") or device()
        if not cc.socket_client.is_connected:
            return None
        if cc.app_id in (None, pychromecast.APP_BACKDROP):
            return "free"
        if cc.app_id == pychromecast.APP_MEDIA_RECEIVER and \
                (cc.media_controller.status.content_id or "").endswith(STREAM_PATH):
            return "ours"
        return "other"
    except Exception:
        return None


def showing_ours():
    """The Chromecast is playing our stream (not stopped, not another app)."""
    try:
        return state() == "ours" and not device().media_controller.status.player_is_idle
    except Exception:
        return False


def quit_if_ours():
    try:
        if state() == "ours":
            device().quit_app()
    except Exception as e:
        print("stop cast:", e, flush=True)
