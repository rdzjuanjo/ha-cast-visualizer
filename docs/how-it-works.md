# How it works

## Audio

`squeezelite` registers in Music Assistant as a Squeezelite player named `player_name`. It plays into a
PulseAudio **null sink** called `vis` inside the container: nothing is heard on the machine itself. The sound
reaches your speakers through the Chromecast, as the audio track of the video stream.

## Image

- `sway` runs **headless** (no monitor) on the GPU render node (`WLR_RENDERER=gles2`), with Xwayland enabled.
- `projectM-pulseaudio` (Qt/X11 app) opens full screen in that session and listens to `vis.monitor`.
- `wf-recorder` grabs the sway output as raw NV12 frames and pipes them to `ffmpeg`.

Why not Xvfb: it renders with llvmpipe (software OpenGL) and eats the CPU. Why not `x11grab` on Xwayland:
it returns black frames.

## Encoding and streaming

`ffmpeg` mixes the frames with the sink's audio and encodes **x264 `veryfast` with a bitrate cap** + AAC into
**HLS with 4 s segments** in `/tmp/hls`, served by the API on `:8099/hls/`.

- `-fps_mode cfr`: wf-recorder only sends a frame when the image changes; this makes the frame rate steady.
- Keyframes are forced every 4 s so all segments are exactly 4 s long (old Chromecasts struggle with
  irregular segments).
- The playlist keeps 8 segments and 8 more files on disk: about one minute of slack if the Chromecast lags.
- VAAPI hardware encoding was tried: on the tested Intel GPU it only allowed constant QP, and some visuals
  produced 30 Mbps spikes that froze a 2nd-gen Chromecast.

## Casting

When at least 3 segments exist (~12 s of buffer) the API casts the playlist to the Default Media Receiver with
PyChromecast. If another app is open on the Chromecast it is closed first, otherwise the stream would play
inside it. The connection is kept open (PyChromecast's discovery must stay alive while connecting) and
re-established once if the Chromecast rebooted.

## Watchers

- **Silence**: while the visualizer runs, the sink level is measured every second. After `silence_seconds`
  of silence it stops; when sound comes back it starts again. Nothing is measured while it is off (measuring
  costs about one CPU core).
- **Other app**: if the Chromecast shows another app for ~10 s, the visualizer stops (the music keeps playing).
  When the Chromecast goes back to its idle screen and music is still playing, the visualizer returns.
- **Current visual**: projectM opens exactly one preset file when it changes visual; inotify on the presets
  folder tells which one is on screen.

## Visual lists

projectM does not walk subfolders, so on every start the API builds a flat folder of symlinks to the presets,
leaving out the removed ones (or keeping only favorites). Lists live in `/data/visualizer/*.txt`.
