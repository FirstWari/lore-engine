#!/usr/bin/env python3
"""lore.py - one command: lecture in, readable notes material out.

    python lore.py <url | video.mp4 | slides.pdf> [--out results]

Given a Coursera/YouTube/any URL, a local video (with an optional .srt next to
it) or a PDF, this writes one folder the calling agent can read directly:

    results/<title>/
        index.json            what was produced, with absolute paths
        transcript.txt        "[HH:MM:SS - HH:MM:SS] text" lines (or "[Page N]" blocks for PDFs)
        transcript.srt        copy of the subtitle file (videos only)
        keyframes/            de-duplicated frames, frame_HH-MM-SS.jpg (or pages/ for PDFs)
        storyboard_page_NN.jpg  3x3 contact sheets with timestamp badges

The last line printed to stdout is always the index.json content as one JSON
line, so a script or agent can parse the result without reading the folder.
No LLM is called; the agent that runs this command writes the notes.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# Make `src` importable when run as `python lore.py` from a clone.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.core.downloader import download_lecture, sanitize_filename  # noqa: E402
from src.core.pdf import extract_pdf_content, get_pdf_info  # noqa: E402
from src.core.storyboard import compile_storyboard_sheets  # noqa: E402
from src.core.transcripts import get_transcript_segment, get_transcript_summary  # noqa: E402
from src.core.video import extract_keyframes, get_video_info  # noqa: E402

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".m4v"}
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _say(message: str, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr, flush=True)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Keyframe selection
# ---------------------------------------------------------------------------

#: (similarity, min_diversity) pHash thresholds, strict to loose. Strict keeps a
#: talking-head lecture down to its slide changes; screen recordings (notebooks,
#: code, terminals) change only a few pixels between meaningful moments, so the
#: ladder relaxes until enough frames survive. Measured on two Coursera lectures:
#: slides 10/16 -> 15 frames; a 28-minute lab session 10/16 -> 4, 3/6 -> 23.
THRESHOLD_LADDER = ((10, 16), (5, 10), (3, 6), (2, 4))


def _min_useful_frames(duration_seconds: float, max_frames: int) -> int:
    """At least one 3x3 sheet, roughly one frame per two minutes, never above max_frames."""
    return max(1, min(max_frames, max(9, int(duration_seconds // 120))))


def _select_keyframes(video_path: Path, keyframes_dir: Path, duration_seconds: float, *,
                      max_frames: int, candidates: int) -> tuple[list[dict[str, Any]], tuple[int, int]]:
    """Walk THRESHOLD_LADDER until enough distinct frames survive; return frames + thresholds used."""
    wanted = _min_useful_frames(duration_seconds, max_frames)
    frames: list[dict[str, Any]] = []
    used = THRESHOLD_LADDER[0]
    for similarity, diversity in THRESHOLD_LADDER:
        shutil.rmtree(keyframes_dir, ignore_errors=True)
        frames = extract_keyframes(
            video_path,
            output_dir=keyframes_dir,
            max_frames=max_frames,
            candidate_samples=candidates,
            similarity_threshold=similarity,
            min_diversity_threshold=diversity,
        )
        used = (similarity, diversity)
        if len(frames) >= wanted:
            break
    return frames, used


# ---------------------------------------------------------------------------
# Video / URL path
# ---------------------------------------------------------------------------

def process_video(
    video_path: Path,
    srt_path: Path | None,
    out_root: Path,
    *,
    title: str | None = None,
    max_frames: int = 27,
    quiet: bool = False,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract transcript text, keyframes and storyboards from a local video."""
    title = sanitize_filename(title or video_path.stem)
    target = out_root / title
    keyframes_dir = target / "keyframes"
    target.mkdir(parents=True, exist_ok=True)

    index: dict[str, Any] = {
        "title": title,
        "kind": "video",
        "source": source or {"input": str(video_path)},
        "output_dir": str(target.resolve()),
        "video_path": str(video_path.resolve()),
        "transcript_txt": None,
        "transcript_srt": None,
        "transcript": None,
        "keyframes": [],
        "storyboard_pages": [],
        "warnings": [],
    }

    # 1. transcript
    if srt_path and srt_path.exists():
        _say("[1/3] Transcript", quiet)
        srt_copy = target / "transcript.srt"
        if srt_path.resolve() != srt_copy.resolve():
            shutil.copyfile(srt_path, srt_copy)
        segment = get_transcript_segment(srt_copy, page=1, page_size=10**6)
        txt = target / "transcript.txt"
        txt.write_text(segment["formatted_text"] + "\n", encoding="utf-8")
        index["transcript_txt"] = str(txt.resolve())
        index["transcript_srt"] = str(srt_copy.resolve())
        index["transcript"] = get_transcript_summary(srt_copy)
    else:
        _say("[1/3] Transcript: no .srt found, skipping", quiet)
        index["warnings"].append("no subtitle file; transcript.txt not written")

    # 2. keyframes (one candidate every ~10 s so long lectures are not under-sampled)
    _say("[2/3] Keyframes", quiet)
    info = get_video_info(video_path)
    index["video"] = {k: info[k] for k in ("duration_seconds", "duration_formatted", "resolution", "fps")}
    candidates = max(60, int(info["duration_seconds"] // 10) + 1)
    frames, thresholds = _select_keyframes(video_path, keyframes_dir, info["duration_seconds"],
                                           max_frames=max_frames, candidates=candidates)
    index["keyframes"] = frames
    index["keyframe_thresholds"] = {"similarity": thresholds[0], "min_diversity": thresholds[1]}

    # 3. storyboard
    _say("[3/3] Storyboard", quiet)
    sheets = compile_storyboard_sheets(frames, output_dir=target, title=f"{title} Storyboard", prefix="storyboard")
    index["storyboard_pages"] = sheets

    _write_json(target / "index.json", index)
    return index


# ---------------------------------------------------------------------------
# PDF path
# ---------------------------------------------------------------------------

def process_pdf(pdf_path: Path, out_root: Path, *, max_frames: int = 27, quiet: bool = False) -> dict[str, Any]:
    """Extract page text and page images from a PDF, plus contact sheets."""
    title = sanitize_filename(pdf_path.stem)
    target = out_root / title
    pages_dir = target / "pages"
    target.mkdir(parents=True, exist_ok=True)

    _say("[1/2] PDF pages", quiet)
    meta = get_pdf_info(pdf_path)
    pages = extract_pdf_content(pdf_path, output_dir=pages_dir, extract_text=True, render_images=True)

    txt = target / "transcript.txt"
    txt.write_text(
        "\n\n".join(f"[Page {p['page_number']}]\n{p['text']}" for p in pages) + "\n",
        encoding="utf-8",
    )

    _say("[2/2] Storyboard", quiet)
    frames = [
        {"timestamp": f"p.{p['page_number']}", "image_path": p["image_path"]}
        for p in pages
        if p.get("image_path")
    ]
    sheets = compile_storyboard_sheets(frames, output_dir=target, title=f"{title} Pages", prefix="storyboard")

    index: dict[str, Any] = {
        "title": title,
        "kind": "pdf",
        "source": {"input": str(pdf_path.resolve()), "total_pages": meta["total_pages"]},
        "output_dir": str(target.resolve()),
        "transcript_txt": str(txt.resolve()),
        "pages": pages,
        "storyboard_pages": sheets,
        "warnings": [],
    }
    _write_json(target / "index.json", index)
    return index


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(
    target: str,
    *,
    out: str = "results",
    quality: str = "720p",
    lang: str = "en",
    cookies: str | None = None,
    max_frames: int = 27,
    quiet: bool = False,
) -> dict[str, Any]:
    out_root = Path(out)
    out_root.mkdir(parents=True, exist_ok=True)

    if _URL_RE.match(target):
        _say(f"[0/3] Downloading {target}", quiet)
        dl = download_lecture(target, output_dir=None, cookie_file=cookies, sub_lang=lang, quality=quality)
        video = Path(dl["video_path"])
        srt = Path(dl["srt_path"]) if dl.get("srt_path") else None
        index = process_video(video, srt, out_root, title=dl.get("title"), max_frames=max_frames,
                              quiet=quiet, source={"url": target, **dl})
        if dl.get("subtitle_error"):
            index["warnings"].append(f"subtitle download failed: {dl['subtitle_error']}")
            _write_json(Path(index["output_dir"]) / "index.json", index)
        return index

    path = Path(target)
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {target}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return process_pdf(path, out_root, max_frames=max_frames, quiet=quiet)
    if suffix in VIDEO_EXTENSIONS:
        srt = path.with_suffix(".srt")
        return process_video(path, srt if srt.exists() else None, out_root, max_frames=max_frames, quiet=quiet)
    if suffix == ".srt":
        raise ValueError("Give the video file; its .srt next to it is picked up automatically.")
    raise ValueError(f"Unsupported input: {target} (expected a URL, a video file or a PDF)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lore",
        description="Turn a lecture URL, video or PDF into transcript.txt + keyframes + storyboard sheets.",
    )
    parser.add_argument("input", help="Coursera/YouTube/any URL, a local video (.srt beside it is used) or a PDF")
    parser.add_argument("--out", default="results", help="results root (default: results)")
    parser.add_argument("--quality", default="720p", help="video quality for downloads (default: 720p)")
    parser.add_argument("--lang", default="en", help="subtitle language for downloads (default: en)")
    parser.add_argument("--cookies", default=None, help="Netscape cookies.txt for Coursera (default: COURSERA_COOKIE_FILE or www.coursera.org_cookies.txt)")
    parser.add_argument("--max-frames", type=int, default=27, help="max keyframes to keep (default: 27 = 3 storyboard pages)")
    parser.add_argument("--json", action="store_true", help="print only the final JSON line")
    args = parser.parse_args(argv)

    try:
        index = run(
            args.input,
            out=args.out,
            quality=args.quality,
            lang=args.lang,
            cookies=args.cookies,
            max_frames=args.max_frames,
            quiet=args.json,
        )
    except Exception as exc:  # noqa: BLE001 - one clear line for the caller
        print(json.dumps({"error": f"{exc.__class__.__name__}: {exc}"}, ensure_ascii=False))
        return 1

    if not args.json:
        print(f"Done: {index['output_dir']}", file=sys.stderr)
    print(json.dumps(index, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
