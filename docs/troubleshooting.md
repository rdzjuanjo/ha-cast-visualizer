# Troubleshooting

**The Chromecast buffers every few seconds.** The stream is on the live edge. Keep the default 4 s segments
and don't lower the 3-segment start buffer. Check that the machine is not overloaded (CPU temperature, other
heavy containers): x264 must keep up in real time.

**The Chromecast freezes after a while.** Usually bitrate spikes or the device falling behind and asking for
deleted segments. Lower `video_bitrate` or the resolution. Old Chromecasts (2nd gen, 512 MB) only handle
H.264 up to 1080p and do best at 480p for this kind of image.

**It casts but the screen is black / projectM logo.** projectM starts on its splash screen and the API asks for a
random visual right after; if it stays there, check the GPU: `/dev/dri/renderD128` must be passed to the
container (`video: true` in the add-on). The log warns when it is missing.

**Nothing is cast.** Check `cast_name` (exact friendly name) and that the container uses the host network.
If the machine has several interfaces, set `host_ip` to the one on the Chromecast's network.

**High CPU while the visualizer is off.** It should be near zero. If music keeps playing while you watch
another app, the visualizer steps aside after ~10 s; if it does not, check the log.

**Spotify Connect stuck on "connecting…".** Restarting the visualizer several times in a row can leave MA's
Spotify Connect for that player in a bad state. Restart Music Assistant and turn the player on again.

**Container logs grow forever.** Use log rotation (`max-size`), as in `docker-compose.example.yml`: with a huge
log, `docker logs` can take minutes and push dockerd to 100 % CPU.

**Files in `/tmp/hls` that the app cannot delete.** Don't create files there as root (e.g. with
`docker exec ... mkdir`): the app runs as user `vis` and a start can fail if it cannot empty the folder.

**"Spotify has reached its limit of 1 concurrent source streams".** MA's Spotify provider streams to one player
at a time. If another player (for example the TV itself via DLNA) still holds the stream, playback on the
visualizer fails: stop that player's queue first.

**The visuals barely move and the sound on the TV is very low.** A newly added player in MA can start with a
low volume, and that volume is the signal projectM and the stream receive. Set it to 100 % (see
[music-assistant.md](music-assistant.md#volume)).
