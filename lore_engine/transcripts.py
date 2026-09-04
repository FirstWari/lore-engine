"""SRT parsing, plain-text rendering and summary statistics."""

from pathlib import Path
from typing import Any

import srt


def parse_srt(srt_path: str | Path) -> list[dict[str, Any]]:
    """Parse an SRT file into a structured list of subtitle entries."""
    path = Path(srt_path)
    if not path.exists():
        raise FileNotFoundError(f"SRT file not found: {srt_path}")

    with open(path, encoding="utf-8", errors="ignore") as f:
        content = f.read()

    subtitles = list(srt.parse(content))
    results = []

    for sub in subtitles:
        start_sec = sub.start.total_seconds()
        end_sec = sub.end.total_seconds()

        # Formatted HH:MM:SS
        sh, sm, ss = int(start_sec // 3600), int((start_sec % 3600) // 60), int(start_sec % 60)
        eh, em, es = int(end_sec // 3600), int((end_sec % 3600) // 60), int(end_sec % 60)

        results.append(
            {
                "index": sub.index,
                "start_seconds": round(start_sec, 2),
                "end_seconds": round(end_sec, 2),
                "start_time": f"{sh:02d}:{sm:02d}:{ss:02d}",
                "end_time": f"{eh:02d}:{em:02d}:{es:02d}",
                "text": sub.content.strip(),
            }
        )

    return results


def get_transcript_segment(
    srt_path: str | Path,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """
    Get transcript text, either within a timestamp window or paginated.
    """
    subs = parse_srt(srt_path)
    total_count = len(subs)

    if start_seconds is not None or end_seconds is not None:
        filtered = []
        for s in subs:
            if start_seconds is not None and s["end_seconds"] < start_seconds:
                continue
            if end_seconds is not None and s["start_seconds"] > end_seconds:
                continue
            filtered.append(s)
        items = filtered
    else:
        # Paginated
        start_idx = (page - 1) * page_size
        items = subs[start_idx : start_idx + page_size]

    formatted_text = "\n".join(
        f"[{item['start_time']} - {item['end_time']}] {item['text']}" for item in items
    )

    return {
        "total_subtitles": total_count,
        "returned_subtitles": len(items),
        "page": page,
        "formatted_text": formatted_text,
        "subtitles": items,
    }


def get_transcript_summary(srt_path: str | Path) -> dict[str, Any]:
    """Get high-level summary statistics of the transcript."""
    subs = parse_srt(srt_path)
    if not subs:
        return {"total_subtitles": 0, "duration": "00:00:00", "word_count": 0}

    total_words = sum(len(s["text"].split()) for s in subs)
    duration_sec = subs[-1]["end_seconds"]
    h, m, s = int(duration_sec // 3600), int((duration_sec % 3600) // 60), int(duration_sec % 60)

    return {
        "total_subtitles": len(subs),
        "start_time": subs[0]["start_time"],
        "end_time": subs[-1]["end_time"],
        "duration_seconds": round(duration_sec, 2),
        "duration_formatted": f"{h:02d}:{m:02d}:{s:02d}",
        "word_count": total_words,
    }
