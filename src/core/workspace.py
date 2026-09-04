"""Workspace and lecture file discovery module for lore-engine."""

from pathlib import Path
from typing import List, Dict, Any, Optional

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm"}

def scan_workspace(
    base_dirs: Optional[List[str | Path]] = None
) -> Dict[str, Any]:
    """
    Scan directories (default: 'downloads', 'assets', 'results') for available lecture media.
    Pairs videos with their matching .srt files if available.
    """
    if base_dirs is None:
        base_dirs = ["downloads", "results", "assets"]

    found_lectures = {}
    standalone_transcripts = []
    standalone_pdfs = []
    storyboards = []

    for bdir in base_dirs:
        p = Path(bdir)
        if not p.exists():
            continue

        for item in p.rglob("*"):
            if not item.is_file():
                continue
                
            suffix = item.suffix.lower()
            name_stem = item.stem

            if suffix in VIDEO_EXTENSIONS:
                srt_match = item.with_suffix(".srt")
                has_srt = srt_match.exists()
                found_lectures[name_stem] = {
                    "title": name_stem,
                    "video_path": str(item.resolve()),
                    "srt_path": str(srt_match.resolve()) if has_srt else None,
                    "has_transcript": has_srt,
                    "size_mb": round(item.stat().st_size / (1024 * 1024), 2)
                }
            elif suffix == ".srt":
                # Check if it was paired with a video
                video_matches = [item.with_suffix(ve) for ve in VIDEO_EXTENSIONS if item.with_suffix(ve).exists()]
                if not video_matches:
                    standalone_transcripts.append({
                        "title": name_stem,
                        "srt_path": str(item.resolve()),
                        "size_kb": round(item.stat().st_size / 1024, 2)
                    })
            elif suffix == ".pdf":
                standalone_pdfs.append({
                    "title": name_stem,
                    "pdf_path": str(item.resolve()),
                    "size_mb": round(item.stat().st_size / (1024 * 1024), 2)
                })
            elif "storyboard" in item.name.lower() and suffix in {".jpg", ".png", ".jpeg"}:
                storyboards.append({
                    "name": item.name,
                    "sheet_path": str(item.resolve()),
                    "parent": item.parent.name
                })

    return {
        "video_lectures": list(found_lectures.values()),
        "standalone_transcripts": standalone_transcripts,
        "pdf_documents": standalone_pdfs,
        "storyboard_sheets": storyboards,
        "total_lectures": len(found_lectures)
    }
