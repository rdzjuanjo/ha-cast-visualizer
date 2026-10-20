"""projectM rendered in a headless sway session (GPU) -> wf-recorder -> ffmpeg x264 -> HLS -> Chromecast.

Audio comes from the PulseAudio null sink `vis`, where squeezelite (the Music Assistant player) plays.
"""
import array
import json
import math
import os
import subprocess
import threading
import time

import cast
import hooks
from config import load

opts = load()
ENV = dict(os.environ)
HLS = "/tmp/hls"
DATA = "/data/visualizer"            # favorites / removed / mode lists
PRESETS_DIR = "/usr/share/projectM/presets"
FLAT = os.path.expanduser("~/presets")
SEGMENT_SECONDS = 4

procs = {}
lock = threading.Lock()
auto = {"stopped_by_silence": False, "stopped_by_other_app": False, "started_at": 0.0}
visual = {"locked": False, "current": ""}


# ---- preset lists ----------------------------------------------------------------------------------------------

def read_list(name):
    path = f"{DATA}/{name}.txt"
    return set(line.strip() for line in open(path)) - {""} if os.path.exists(path) else set()


def write_list(name, values):
    os.makedirs(DATA, exist_ok=True)
    open(f"{DATA}/{name}.txt", "w").write("\n".join(sorted(values)) + "\n")


def all_presets():
    found = {}
    for root, _, files in os.walk(PRESETS_DIR):
        for f in files:
            if f.endswith((".milk", ".prjm")) and f not in found:
                found[f] = f"{root}/{f}"
    return found


def build_presets():
    """projectM does not walk subfolders: flat folder of symlinks, without removed ones (or only favorites)."""
    every = all_presets()
    removed, favorites = read_list("removed"), read_list("favorites")
    chosen = [n for n in every if n not in removed]
    if read_list("mode") == {"favorites"} and favorites & set(chosen):
        chosen = [n for n in chosen if n in favorites]
    if os.path.isdir(FLAT):
        for f in os.listdir(FLAT):
            os.remove(f"{FLAT}/{f}")
    os.makedirs(FLAT, exist_ok=True)
    for n in chosen:
        os.symlink(every[n], f"{FLAT}/{n}")
    return len(chosen)


def projectm_config():
    d = os.path.expanduser("~/.projectM")
    os.makedirs(d, exist_ok=True)
    build_presets()
    values = {"Window Width": str(opts["width"]), "Window Height": str(opts["height"]), "FPS": str(opts["fps"]),
              "Fullscreen": "false", "Preset Duration": str(opts["preset_duration"]), "Smooth Preset Duration": "5",
              "Hard Cut Sensitivity": "10", "Aspect Correction": "true", "Preset Path": FLAT, "Shuffle Enabled": "1"}
    out = []
    for line in open("/usr/share/projectM/config.inp").read().splitlines():
        key = line.split("=")[0].strip()
        out.append(f"{key} = {values[key]}" if key in values else line)
    open(f"{d}/config.inp", "w").write("\n".join(out) + "\n")


# ---- projectM control (keys through Xwayland) ------------------------------------------------------------------

def projectm_key(key):
    """n = next, p = previous, r = random, l = lock."""
    w = subprocess.run(["xdotool", "search", "--name", "^projectM$"], capture_output=True, text=True,
                       env=ENV).stdout.split()
    if not w:
        raise RuntimeError("projectM is not running (no music)")
    subprocess.run(["xdotool", "key", "--window", w[0], key], env=ENV, check=True)


def first_preset():
    """projectM starts on its splash screen: ask for a random visual right away."""
    visual["current"] = ""
    for _ in range(10):
        time.sleep(1)
        try:
            projectm_key("r")
            return
        except Exception:
            pass


def start_projectm():
    projectm_config()
    visual["locked"] = False
    procs["projectm"] = subprocess.Popen(["projectM-pulseaudio"], env=ENV,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    first_preset()


def restart_projectm():
    """Apply list changes now (projectM only reads its folder on start)."""
    p = procs.get("projectm")
    if p is None or p.poll() is not None:
        return
    p.terminate()
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:   # it does not always honor SIGTERM
        p.kill()
        p.wait(timeout=5)
    start_projectm()


def watch_presets():
    """projectM opens exactly one preset file when it changes visual: that is how we know which one is showing."""
    import ctypes
    import select
    import struct
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    fd = libc.inotify_init1(os.O_NONBLOCK)
    for root, _, _ in os.walk(PRESETS_DIR):
        libc.inotify_add_watch(fd, root.encode(), 0x20)  # IN_OPEN
    while True:
        select.select([fd], [], [])
        buf = os.read(fd, 65536)
        i = 0
        while i < len(buf):
            _, _, _, ln = struct.unpack_from("iIII", buf, i)
            name = buf[i + 16:i + 16 + ln].rstrip(b"\0").decode(errors="ignore")
            i += 16 + ln
            if name.endswith((".milk", ".prjm")):
                visual["current"] = name


def pretty(name):
    return os.path.splitext(name)[0].replace("_", " ") if name else ""


def control(action):
    running = procs.get("projectm") is not None and procs["projectm"].poll() is None
    current = visual["current"] if running else ""
    if action == "current":
        return pretty(current) or "none"
    if action == "remove":
        if not current:
            return "current visual unknown"
        write_list("removed", read_list("removed") | {current})
        write_list("favorites", read_list("favorites") - {current})
        if os.path.lexists(f"{FLAT}/{current}"):
            os.remove(f"{FLAT}/{current}")
        projectm_key("n")
        return f"removed: {pretty(current)}"
    if action == "favorite":
        if not current:
            return "current visual unknown"
        write_list("favorites", read_list("favorites") | {current})
        return f"favorite: {pretty(current)}"
    if action == "unfavorite":
        write_list("favorites", read_list("favorites") - {current})
        return f"no longer favorite: {pretty(current)}"
    if action in ("only_favorites", "all"):
        if action == "only_favorites" and not read_list("favorites"):
            return "no favorites yet"
        write_list("mode", {"favorites"} if action == "only_favorites" else {"all"})
        n = build_presets()
        restart_projectm()
        return f"{'only favorites' if action == 'only_favorites' else 'all visuals'} ({n})"
    if action == "mode":
        return "only_favorites" if read_list("mode") == {"favorites"} else "all"
    if action == "summary":
        return json.dumps({"current": pretty(current), "file": current, "favorite": current in read_list("favorites"),
                           "mode": control("mode"), "favorites": len(read_list("favorites")),
                           "removed": len(read_list("removed")), "locked": visual["locked"]}, ensure_ascii=False)
    if action == "lock":
        if not visual["locked"]:
            projectm_key("l")
            visual["locked"] = True
        return "visual locked"
    if action == "unlock":
        if visual["locked"]:
            projectm_key("l")
            visual["locked"] = False
        return "visual unlocked"
    projectm_key({"next": "n", "previous": "p", "random": "r"}[action])
    return f"visual {action}"


CONTROL_ACTIONS = ("next", "previous", "random", "lock", "unlock", "current", "remove", "favorite", "unfavorite",
                   "only_favorites", "all", "mode", "summary")


# ---- stream ----------------------------------------------------------------------------------------------------

def running():
    return procs.get("ffmpeg") is not None and procs["ffmpeg"].poll() is None


def segments_ready():
    try:
        return open(f"{HLS}/stream.m3u8").read().count("#EXTINF")
    except OSError:
        return 0


def _kill_all():
    for name, p in procs.items():
        if p.poll() is None:
            if name == "ffmpeg":
                # wf-recorder ignores SIGTERM while it waits for a frame (e.g. projectM did not start)
                try:
                    os.killpg(p.pid, 15)
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, 9)
                except OSError:
                    pass
            else:
                p.kill()
                p.wait(timeout=5)
    procs.clear()


def start():
    with lock:
        if running():
            if cast.showing_ours():
                return "already running"
            cast.cast_stream()
            return "already running: cast again"
        # a projectM left over from a failed start (without ffmpeg) is closed before opening another one
        if "projectm" in procs and procs["projectm"].poll() is None:
            p = procs.pop("projectm")
            p.kill()
            p.wait(timeout=5)
        start_projectm()
        # empty the folder without deleting it: if it belonged to another user it could not be removed
        os.makedirs(HLS, exist_ok=True)
        for f in os.listdir(HLS):
            try:
                os.remove(f"{HLS}/{f}")
            except OSError:
                pass
        fps, kbps = opts["fps"], opts["video_bitrate"]
        # wf-recorder only delivers frames when the image changes: -fps_mode cfr makes them steady, and forced
        # keyframes give exact segments (old Chromecasts struggle with irregular ones). x264 with a bitrate cap:
        # VAAPI here only allowed CQP, whose spikes (up to 30 Mbps) froze the Chromecast.
        procs["ffmpeg"] = subprocess.Popen(["bash", "-c",
            f"wf-recorder -y -c rawvideo -x nv12 -r {fps} -m nut -f /dev/stdout 2>/dev/null | "
            "ffmpeg -loglevel error -f nut -i - "
            f"-f pulse -i vis.monitor -map 0:v -map 1:a -fps_mode cfr -r {fps} "
            "-c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p "
            f"-b:v {kbps}k -maxrate {int(kbps * 1.1)}k -bufsize {kbps * 2}k -g {fps * SEGMENT_SECONDS} "
            f"-sc_threshold 0 -force_key_frames 'expr:gte(t,n_forced*{SEGMENT_SECONDS})' "
            f"-af aresample=async=1 -c:a aac -b:a 192k -f hls -hls_time {SEGMENT_SECONDS} "
            "-hls_list_size 8 -hls_delete_threshold 8 "
            f"-hls_flags delete_segments+omit_endlist+independent_segments {HLS}/stream.m3u8"],
            env=ENV, start_new_session=True)
        # cast with 3 segments (~12 s) of buffer: with 2 s segments the Chromecast sat on the live edge waiting
        # for each one (buffering every few seconds) and, if it fell behind, asked for deleted segments and froze
        for _ in range(60):
            if segments_ready() >= 3:
                break
            time.sleep(0.5)
        try:
            cast.cast_stream()
        except Exception:
            _kill_all()
            raise
        auto["started_at"] = time.time()
    hooks.fire("start")
    return "casting"


def stop():
    cast.quit_if_ours()
    with lock:
        was_running = running()
        _kill_all()
    if was_running:
        hooks.fire("stop")
    return "stopped"


def manual(on):
    """Start/stop requested by the user (API): the automatic resume is forgotten."""
    auto["stopped_by_silence"] = auto["stopped_by_other_app"] = False
    return start() if on else stop()


# ---- watchers --------------------------------------------------------------------------------------------------

def audio_level(seconds=1.0):
    """RMS level (0-32768) of the player's sink during `seconds`."""
    try:
        out = subprocess.run(["timeout", str(seconds), "parec", "-d", "vis.monitor", "--raw",
                              "--format=s16le", "--rate=22050", "--channels=1"],
                             capture_output=True, env=ENV).stdout
        a = array.array("h", out[: len(out) // 2 * 2])
        return math.sqrt(sum(x * x for x in a) / len(a)) if a else 0.0
    except Exception:
        return 0.0


def _safe(fn, what):
    try:
        fn()
    except Exception as e:
        print(f"{what}:", e, flush=True)


def watch_other_app(is_running, playing, n):
    """Something else sent to the Chromecast -> stop the visualizer (the music keeps playing) to save CPU;
    when that app is closed and the music is still playing -> put the visualizer back."""
    if is_running and time.time() - auto["started_at"] > 20:
        n["other"] = n["other"] + 1 if cast.state() == "other" else 0
        if n["other"] >= 2:
            print("another app on the Chromecast: stopping the visualizer", flush=True)
            _safe(stop, "watch other app")
            auto["stopped_by_other_app"] = True
            n["other"] = 0
    elif auto["stopped_by_other_app"] and not is_running:
        if not playing:
            n["free"] = 0
            return
        n["free"] = n["free"] + 1 if cast.state() == "free" else 0
        if n["free"] >= 2:
            print("Chromecast free again and music still playing: visualizer back", flush=True)
            auto["stopped_by_other_app"] = False
            _safe(start, "watch other app resume")
            n["free"] = 0


def watcher():
    """Stops the visualizer after `silence_seconds` without sound (pause) and resumes it when sound comes back."""
    silence, loops = 0, 0
    n = {"other": 0, "free": 0}
    while True:
        is_running = running()
        if not is_running and not auto["stopped_by_silence"] and not auto["stopped_by_other_app"]:
            # nothing to watch: measuring audio every second costs about one CPU core
            time.sleep(1)
            continue
        playing = audio_level() > 30
        loops += 1
        if loops % 5 == 0:   # the Chromecast is checked every ~5 s
            watch_other_app(is_running, playing, n)
        if auto["stopped_by_other_app"] and not is_running:
            # no music for a while: nothing left to resume
            silence = 0 if playing else silence + 1
            if silence >= 60:
                auto["stopped_by_other_app"] = False
                silence = 0
            continue
        if is_running:
            silence = 0 if playing else silence + 1
            if silence >= opts["silence_seconds"]:
                print(f"{opts['silence_seconds']} s of silence: stopping", flush=True)
                _safe(stop, "watcher stop")
                auto["stopped_by_silence"] = True
                silence = 0
        elif auto["stopped_by_silence"] and playing:
            print("sound is back: resuming", flush=True)
            auto["stopped_by_silence"] = False
            _safe(start, "watcher start")
        else:
            time.sleep(1)
