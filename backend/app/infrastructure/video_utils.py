import logging
import re
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

log = logging.getLogger(__name__)

MAX_SECONDS = 60      # only the first minute is used
REALTIME_MAX = 8      # clips up to this long are sent as normal video
TARGET_FRAMES = 16    # longer clips are condensed into this many evenly spaced frames
MAX_WIDTH = 640

_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_TAIL = [
    "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
]


def _duration(ffmpeg: str, src: Path) -> float | None:
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-i", str(src)], capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None
    m = _DURATION.search(proc.stderr.decode(errors="ignore"))
    if not m:
        return None
    h, mnt, sec = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(sec)


def _run(cmd: list[str], dst: Path) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise ValueError("Processing the video took too long. Try a shorter clip.") from None
    if proc.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
        return True
    log.warning("ffmpeg failed: %s", proc.stderr.decode(errors="ignore")[-500:])
    return False


def prepare_video(raw: bytes) -> bytes:
    """Shrink and strip audio. Short clips stay real-time; long ones become ~16 evenly spaced frames."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    scale = f"scale='min({MAX_WIDTH},iw)':-2"
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "input", Path(tmp) / "clip.mp4"
        src.write_bytes(raw)
        secs = min(_duration(ffmpeg, src) or REALTIME_MAX, MAX_SECONDS)

        if secs <= REALTIME_MAX:
            variants = [["-t", str(REALTIME_MAX), "-i", str(src), "-vf", scale]]
        else:
            rate = TARGET_FRAMES / secs
            condensed = [
                "-t", str(MAX_SECONDS), "-i", str(src),
                "-vf", f"fps={rate:.5f},setpts=N/(2*TB),{scale}", "-r", "2",
            ]
            # First try decoding keyframes only (much faster); fall back to a full decode.
            variants = [["-skip_frame", "nokey", *condensed], condensed]

        for opts in variants:
            dst.unlink(missing_ok=True)
            if _run([ffmpeg, "-y", "-v", "error", *opts, *_TAIL, str(dst)], dst):
                return dst.read_bytes()
    raise ValueError("Could not read the video file.")