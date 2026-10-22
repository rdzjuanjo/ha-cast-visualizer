#!/bin/bash
# Starts a headless sway session (GPU through gles2, Xwayland on :1), PulseAudio with a null sink and squeezelite
# (the Music Assistant player). projectM and ffmpeg are launched by the API on demand.
set -e
eval "$(python3 /app/config.py --shell)"

id vis >/dev/null 2>&1 || useradd -m -G audio,video vis
# the render node's group differs between hosts: give vis that group, whatever its id is
if [ -e /dev/dri/renderD128 ]; then
  gid=$(stat -c %g /dev/dri/renderD128)
  getent group "$gid" >/dev/null || groupadd -g "$gid" render-host
  usermod -aG "$(getent group "$gid" | cut -d: -f1)" vis
else
  echo "WARNING: /dev/dri/renderD128 not found: sway will fall back to software rendering (very slow)"
fi
rm -rf /tmp/xdg /tmp/.X11-unix/X* /tmp/.X*-lock
install -d -m 700 -o vis -g vis /tmp/xdg
install -d -o vis -g vis /data/visualizer
cat > /tmp/sway.cfg <<CFG
output HEADLESS-1 resolution ${CV_WIDTH}x${CV_HEIGHT}
xwayland enable
default_border none
for_window [class=".*"] fullscreen enable
for_window [title=".*"] fullscreen enable
CFG

# squeezelite would take the MAC of the host interface: with host networking every instance (and any other
# squeezelite on the machine) gets the same one and Music Assistant merges them. Derive a stable, locally
# administered MAC from the player name instead.
mac=$(printf %s "$CV_PLAYER_NAME" | md5sum | sed -E 's/^(..)(..)(..)(..)(..).*/02:\1:\2:\3:\4:\5/')

exec runuser -u vis -- env XDG_RUNTIME_DIR=/tmp/xdg PLAYER_NAME="$CV_PLAYER_NAME" PLAYER_MAC="$mac" bash -c '
  pulseaudio -D --exit-idle-time=-1 --log-target=stderr
  sleep 2
  pactl load-module module-null-sink sink_name=vis sink_properties=device.description=Visualizer
  pactl set-default-sink vis
  pactl set-default-source vis.monitor
  WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 WLR_RENDERER=gles2 \
    WLR_RENDER_DRM_DEVICE=/dev/dri/renderD128 sway -c /tmp/sway.cfg >/tmp/sway.log 2>&1 &
  # Xwayland takes the first free display (:0, or :1 when the host X server is visible through host networking)
  for _ in $(seq 20); do ls /tmp/.X11-unix/X* >/dev/null 2>&1 && break; sleep 0.5; done
  display=":$(ls /tmp/.X11-unix | sed -n "s/^X//p" | sort -n | tail -1)"
  echo "Xwayland on $display"
  squeezelite -n "$PLAYER_NAME" -m "$PLAYER_MAC" -o default -a 200 -C 5 &
  cd /app
  exec env WAYLAND_DISPLAY=wayland-1 DISPLAY="$display" /opt/venv/bin/python server.py'
