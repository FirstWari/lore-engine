"""Video keyframe and timestamp extraction module for lore-engine."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
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

def parse_time_to_seconds(time_val: str | float | int) -> float:
    """Convert timestamp string (HH:MM:SS or MM:SS or seconds) to float seconds."""
    if isinstance(time_val, (int, float)):
        return float(time_val)
    
    parts = str(time_val).strip().split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 1:
        return float(parts[0])
    raise ValueError(f"Invalid timestamp format: {time_val}")

def format_seconds_to_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS."""
    sec = int(seconds)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_video_info(video_path: str | Path) -> Dict[str, Any]:
    """Get metadata for a video file (fps, duration, resolution, total frames)."""
    if PyVideoReader is None:
        raise ImportError("video-reader-rs library is required. Install via uv.")

    path = str(Path(video_path).resolve())
    with suppress_stderr():
        vr = PyVideoReader(path, threads=0)
    
    shape = vr.get_shape()  # (frames, height, width, channels)
    info = vr.get_info()
    fps = float(info.get("fps", 30.0))
    total_frames = shape[0]
    height = shape[1] if len(shape) > 1 else 0
    width = shape[2] if len(shape) > 2 else 0
    duration_sec = total_frames / fps if fps > 0 else 0

    return {
        "video_path": path,
        "total_frames": total_frames,
        "fps": round(fps, 2),
        "duration_seconds": round(duration_sec, 2),
        "duration_formatted": format_seconds_to_timestamp(duration_sec),
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height
    }

def extract_frame_at_timestamp(
    video_path: str | Path,
    timestamp: str | float,
    output_path: Optional[str | Path] = None
) -> Dict[str, Any]:
    """Extract a single frame from video at the given timestamp."""
    if PyVideoReader is None:
        raise ImportError("video-reader-rs library is required.")

    target_sec = parse_time_to_seconds(timestamp)
    path = str(Path(video_path).resolve())

    with suppress_stderr():
        vr = PyVideoReader(path, threads=0)

    shape = vr.get_shape()
    total_frames = shape[0]
    fps = float(vr.get_info().get("fps", 30.0))

    frame_idx = int(target_sec * fps)
    frame_idx = max(0, min(frame_idx, total_frames - 1))
    actual_sec = frame_idx / fps

    with suppress_stderr():
        frame = vr[frame_idx]

    pil_img = Image.fromarray(frame)

    ts_str = format_seconds_to_timestamp(actual_sec).replace(":", "-")
    if not output_path:
        stem = Path(video_path).stem
        out_dir = Path("results") / stem / "frames"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"frame_{ts_str}.jpg"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    pil_img.save(str(output_path), "JPEG", quality=90)

    return {
        "timestamp": format_seconds_to_timestamp(actual_sec),
        "seconds": round(actual_sec, 2),
        "frame_index": frame_idx,
        "image_path": str(output_path.resolve())
    }

def extract_keyframes(
    video_path: str | Path,
    output_dir: Optional[str | Path] = None,
    start_seconds: float = 0.0,
    end_seconds: Optional[float] = None,
    max_frames: int = 25,
    similarity_threshold: int = 5,
    min_diversity_threshold: int = 10,
    candidate_samples: int = 60
) -> List[Dict[str, Any]]:
    """
    Extract diverse, non-duplicate keyframes from video using perceptual hashing.
    """
    if PyVideoReader is None:
        raise ImportError("video-reader-rs is required.")
    if imagehash is None:
        raise ImportError("imagehash is required.")

    path = str(Path(video_path).resolve())
    with suppress_stderr():
        vr = PyVideoReader(path, threads=0)

    shape = vr.get_shape()
    total_video_frames = shape[0]
    fps = float(vr.get_info().get("fps", 30.0))
    total_sec = total_video_frames / fps

    if end_seconds is None or end_seconds > total_sec:
        end_seconds = total_sec

    start_idx = max(0, min(int(start_seconds * fps), total_video_frames - 1))
    end_idx = max(0, min(int(end_seconds * fps), total_video_frames - 1))

    if end_idx <= start_idx:
        return []

    # Sample candidate indices evenly
    total_chunk_frames = end_idx - start_idx
    num_samples = min(candidate_samples, total_chunk_frames)
    step = max(1, total_chunk_frames // num_samples)
    frame_indices = [start_idx + i * step for i in range(num_samples) if start_idx + i * step < end_idx]

    if not frame_indices:
        return []

    with suppress_stderr():
        frames_batch = vr.get_batch(frame_indices)

    candidates = []
    for i, f_idx in enumerate(frame_indices):
        frame = frames_batch[i]
        curr_sec = f_idx / fps
        img = Image.fromarray(frame)
        h = imagehash.phash(img, hash_size=PHASH_SIZE, highfreq_factor=PHASH_HIGHFREQ_FACTOR)
        candidates.append((h, img, curr_sec, f_idx))

    # Diversity selection
    selected = []
    if candidates:
        selected.append(candidates.pop(0))

    while len(selected) < max_frames and candidates:
        last_hash = selected[-1][0]
        # Prune candidates too close to the last picked frame
        candidates = [c for c in candidates if (c[0] - last_hash) > similarity_threshold]
        if not candidates:
            break

        # Calculate min distance of each candidate to all selected
        selected_hashes = [s[0] for s in selected]
        distances = [min(c[0] - sh for sh in selected_hashes) for c in candidates]
        max_dist = max(distances)
        best_idx = distances.index(max_dist)

        if max_dist >= min_diversity_threshold:
            selected.append(candidates.pop(best_idx))
        else:
            break

    # Save selected frames
    if output_dir is None:
        stem = Path(video_path).stem
        output_dir = Path("results") / stem / "keyframes"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    # Sort selected frames chronologically
    selected.sort(key=lambda x: x[2])

    for _, img, sec, f_idx in selected:
        ts_formatted = format_seconds_to_timestamp(sec)
        ts_filename = ts_formatted.replace(":", "-")
        filepath = output_dir / f"frame_{ts_filename}.jpg"
        img.save(str(filepath), "JPEG", quality=85)
        results.append({
            "timestamp": ts_formatted,
            "seconds": round(sec, 2),
            "frame_index": f_idx,
            "image_path": str(filepath.resolve())
        })

    return results
