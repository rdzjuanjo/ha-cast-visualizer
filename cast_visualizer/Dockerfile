# Cast Visualizer: squeezelite (Music Assistant player) -> PulseAudio -> projectM (headless sway, GPU)
# -> ffmpeg x264 -> HLS -> Chromecast. HTTP API on :8099 (configurable).
ARG BUILD_FROM=debian:trixie
FROM ${BUILD_FROM}
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      squeezelite pulseaudio pulseaudio-utils libasound2-plugins alsa-utils \
      projectm-pulseaudio projectm-data xdotool ffmpeg sway xwayland wf-recorder \
      libgl1-mesa-dri libegl1 python3 python3-venv procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir pychromecast
COPY rootfs/asound.conf /etc/asound.conf
COPY rootfs/entrypoint.sh /entrypoint.sh
COPY app/ /app/
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
