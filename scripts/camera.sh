#!/usr/bin/env bash
#
# camera.sh — capture a still or live-stream from the onboard Pi camera (CSI/IMX219)
# directly into the terminal.
#
# Usage:
#   scripts/camera.sh --still [output.jpg]    Capture a still, render it inline (chafa)
#   scripts/camera.sh --stream                Live-stream to the terminal (mpv)
#
# Options:
#   --width N     Capture width  (still default: full sensor, stream default: 640)
#   --height N    Capture height (still default: full sensor, stream default: 480)
#   --fps N       Stream framerate (default: 15)
#   --no-show     With --still: capture only, skip the terminal render
#   --vo NAME     Stream renderer: tct (default, works everywhere), kitty
#                 (real pixels, kitty terminal only — can crash kitty over
#                 SSH / on older builds), sixel
#   --tuning F    libcamera tuning file (default: imx219_noir.json — the
#                 onboard module is a NoIR; the stock tuning renders
#                 everything magenta from IR contamination)
#
# Rendering:
#   --still  -> chafa (auto-detects kitty graphics / sixel / symbols)
#   --stream -> mpv --vo=tct truecolor half-blocks unless --vo says otherwise

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_ROOT="$( dirname "${DIR}" )"
LOG_DIR="${REPO_ROOT}/tmp/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/camera.log"

log() { echo "$(date -Iseconds) camera.sh: $*" | tee -a "${LOG_FILE}" >&2; }

usage() {
  sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 1
}

# Ctrl-C is the normal way to stop --stream; exit cleanly without a stack of errors
trap 'log "interrupted by user"; exit 0' INT

mode=""
output=""
width=""
height=""
fps=15
show=1
vo="tct"
tuning="/usr/share/libcamera/ipa/rpi/vc4/imx219_noir.json"

while [ $# -gt 0 ]; do
  case "$1" in
    --still)   mode="still" ;;
    --stream)  mode="stream" ;;
    --width)   width="$2"; shift ;;
    --height)  height="$2"; shift ;;
    --fps)     fps="$2"; shift ;;
    --vo)      vo="$2"; shift ;;
    --tuning)  tuning="$2"; shift ;;
    --no-show) show=0 ;;
    -h|--help) usage ;;
    -*)        log "unknown option: $1"; usage ;;
    *)         output="$1" ;;
  esac
  shift
done

[ -n "${mode}" ] || usage

if ! command -v rpicam-still > /dev/null; then
  log "ERROR: rpicam-apps not installed (sudo apt-get install rpicam-apps)"
  exit 1
fi

capture_still() {
  if [ -z "${output}" ]; then
    mkdir -p "${REPO_ROOT}/tmp/camera"
    output="${REPO_ROOT}/tmp/camera/still-$(date +%Y%m%dT%H%M%S).jpg"
  fi

  local args=(-n -t 2000 -o "${output}")
  [ -n "${tuning}" ] && args+=(--tuning-file "${tuning}")
  [ -n "${width}" ]  && args+=(--width "${width}")
  [ -n "${height}" ] && args+=(--height "${height}")

  log "capturing still -> ${output} (${width:-full}x${height:-full})"
  rpicam-still "${args[@]}" >> "${LOG_FILE}" 2>&1
  log "captured $(du -h "${output}" | cut -f1) -> ${output}"
  echo "${output}"

  if [ "${show}" -eq 1 ]; then
    if command -v chafa > /dev/null; then
      chafa "${output}"
    else
      log "chafa not installed; skipping terminal render (sudo apt-get install chafa)"
    fi
  fi
}

stream() {
  if ! command -v mpv > /dev/null; then
    log "ERROR: mpv not installed (sudo apt-get install mpv)"
    exit 1
  fi

  local w="${width:-640}" h="${height:-480}"
  local vargs=(-n -t 0 --codec mjpeg --width "${w}" --height "${h}" --framerate "${fps}")
  [ -n "${tuning}" ] && vargs+=(--tuning-file "${tuning}")

  log "streaming ${w}x${h}@${fps}fps via mpv --vo=${vo} (Ctrl-C to stop)"
  rpicam-vid "${vargs[@]}" -o - 2>> "${LOG_FILE}" \
    | mpv --demuxer-lavf-format=mjpeg --vo="${vo}" --profile=low-latency \
        --untimed --really-quiet -
  log "stream ended"
}

case "${mode}" in
  still)  capture_still ;;
  stream) stream ;;
esac
