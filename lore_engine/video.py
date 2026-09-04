"""Video metadata and perceptual-hash keyframe extraction.

Memory model: candidate frames are decoded in small batches, reduced to a
64-bit perceptual hash immediately and discarded. Only the frames that win the
diversity selection (at most ``max_frames``) are decoded a second time at full
resolution for saving. A two-hour 1080p lecture therefore costs a few hundred
MB at peak instead of many GB, on any machine.
"""

import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from PIL import Image

try:
    import imagehash
except ImportError:
    imagehash = None

try:
    from video_reader import PyVideoReader
except ImportError:
    PyVideoReader = None

logger = logging.getLogger(__name__)

PHASH_SIZE = 8
PHASH_HIGHFREQ_FACTOR = 4
#: Frames decoded per batch while hashing candidates. 32 x 1080p RGB ~ 200 MB.
HASH_BATCH = 32


@contextmanager
def suppress_stderr():
    """Suppress stderr at file descriptor level to mute noisy FFmpeg output."""
    stderr_fd = sys.stderr.fileno()
    stderr_backup_fd = os.dup(stderr_fd)
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, stderr_fd)
        os.close(devnull)
        yield
    finally:
        os.dup2(stderr_backup_fd, stderr_fd)
        os.close(stderr_backup_fd)


def format_seconds_to_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS."""
    sec = int(seconds)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _open(video_path: str | Path):
    if PyVideoReader is None:
        raise ImportError("video-reader-rs is required (run `uv sync` in the repo).")
    path = str(Path(video_path).resolve())
    with suppress_stderr():
        return PyVideoReader(path, threads=0)


def get_video_info(video_path: str | Path) -> dict[str, Any]:
    """Get metadata for a video file (fps, duration, resolution, total frames)."""
    vr = _open(video_path)
    shape = vr.get_shape()  # (frames, height, width, channels)
    info = vr.get_info()
    fps = float(info.get("fps", 30.0))
    total_frames = shape[0]
    height = shape[1] if len(shape) > 1 else 0
    width = shape[2] if len(shape) > 2 else 0
    duration_sec = total_frames / fps if fps > 0 else 0

    return {
        "video_path": str(Path(video_path).resolve()),
        "total_frames": total_frames,
        "fps": round(fps, 2),
        "duration_seconds": round(duration_sec, 2),
        "duration_formatted": format_seconds_to_timestamp(duration_sec),
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height,
    }


def pick_diverse(
    hashes: list[Any],
    max_frames: int,
    similarity_threshold: int,
    min_diversity_threshold: int,
) -> list[int]:
    """Greedy diversity selection over perceptual hashes; returns chosen positions in time order.

    Always keeps the first candidate. Then repeatedly drops candidates within
    ``similarity_threshold`` of the last pick and takes the candidate farthest
    (min Hamming distance) from everything picked so far, stopping when that
    distance falls below ``min_diversity_threshold`` or ``max_frames`` is reached.
    """
    if not hashes:
        return []
    remaining = list(range(1, len(hashes)))
    picked = [0]
    while len(picked) < max_frames and remaining:
        last = hashes[picked[-1]]
        remaining = [i for i in remaining if (hashes[i] - last) > similarity_threshold]
        if not remaining:
            break
        picked_hashes = [hashes[i] for i in picked]
        distances = [min(hashes[i] - ph for ph in picked_hashes) for i in remaining]
        best = max(range(len(remaining)), key=distances.__getitem__)
        if distances[best] < min_diversity_threshold:
            break
        picked.append(remaining.pop(best))
    return sorted(picked)


def extract_keyframes(
    video_path: str | Path,
    output_dir: str | Path | None = None,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    max_frames: int = 25,
    similarity_threshold: int = 5,
    min_diversity_threshold: int = 10,
    candidate_samples: int = 60,
) -> list[dict[str, Any]]:
    """Extract diverse, non-duplicate keyframes from a video using perceptual hashing."""
    if imagehash is None:
        raise ImportError("imagehash is required (run `uv sync` in the repo).")

    vr = _open(video_path)
    total_video_frames = vr.get_shape()[0]
    fps = float(vr.get_info().get("fps", 30.0))
    total_sec = total_video_frames / fps

    if end_seconds is None or end_seconds > total_sec:
        end_seconds = total_sec
    start_idx = max(0, min(int(start_seconds * fps), total_video_frames - 1))
    end_idx = max(0, min(int(end_seconds * fps), total_video_frames - 1))
    if end_idx <= start_idx:
        return []

    # Evenly spaced candidate frame indices.
    span = end_idx - start_idx
    num_samples = min(candidate_samples, span)
    step = max(1, span // num_samples)
    frame_indices = [start_idx + i * step for i in range(num_samples) if start_idx + i * step < end_idx]
    if not frame_indices:
        return []

    # Pass 1: hash candidates batch by batch, never holding more than HASH_BATCH frames.
    hashes: list[Any] = []
    for i in range(0, len(frame_indices), HASH_BATCH):
        batch_idx = frame_indices[i : i + HASH_BATCH]
        with suppress_stderr():
            batch = vr.get_batch(batch_idx)
        for frame in batch:
            hashes.append(
                imagehash.phash(
                    Image.fromarray(frame), hash_size=PHASH_SIZE, highfreq_factor=PHASH_HIGHFREQ_FACTOR
                )
            )
        del batch

    chosen = pick_diverse(hashes, max_frames, similarity_threshold, min_diversity_threshold)
    if not chosen:
        return []

    # Pass 2: decode only the winners at full resolution and save them.
    if output_dir is None:
        output_dir = Path("results") / Path(video_path).stem / "keyframes"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chosen_indices = [frame_indices[i] for i in chosen]
    with suppress_stderr():
        winners = vr.get_batch(chosen_indices)

    results = []
    for f_idx, frame in zip(chosen_indices, winners, strict=False):
        sec = f_idx / fps
        ts = format_seconds_to_timestamp(sec)
        filepath = output_dir / f"frame_{ts.replace(':', '-')}.jpg"
        Image.fromarray(frame).save(str(filepath), "JPEG", quality=85)
        results.append(
            {
                "timestamp": ts,
                "seconds": round(sec, 2),
                "frame_index": f_idx,
                "image_path": str(filepath.resolve()),
            }
        )
    return results
