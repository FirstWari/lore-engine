"""Model Context Protocol (MCP) server for lore-engine.

Exposes educational media extraction tools, resources, and prompts to external LLMs
(Claude Desktop, Cursor, Antigravity, Gemini, Windsurf, etc.) without requiring any internal LLM.
"""

import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from mcp.server.mcpserver import MCPServer

from src.core.workspace import scan_workspace
from src.core.transcripts import (
    search_transcript as core_search_transcript,
    get_transcript_segment,
    get_transcript_summary as core_transcript_summary
)
from src.core.video import (
    get_video_info,
    extract_keyframes as core_extract_keyframes,
    extract_frame_at_timestamp as core_extract_frame,
    parse_time_to_seconds
)
from src.core.storyboard import compile_storyboard_sheets
from src.core.pdf import (
    get_pdf_info,
    extract_pdf_content as core_extract_pdf
)
from src.core.downloader import download_coursera_media

# Initialize MCP Server
server = MCPServer(
    name="lore-engine",
    version="0.2.0",
    description="Multimodal educational content extraction engine (video, transcripts, PDFs, storyboards)"
)

# ---------------------------------------------------------------------------
# TOOLS: Workspace & Discovery
# ---------------------------------------------------------------------------

@server.tool(
    name="list_lectures",
    description="Scan the workspace for educational content: video lectures, SRT transcripts, PDFs, and generated storyboards."
)
def list_lectures(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """List all available lecture files and assets in the workspace."""
    search_dirs = [base_dir] if base_dir else ["downloads", "results", "assets"]
    return scan_workspace(search_dirs)

# ---------------------------------------------------------------------------
# TOOLS: Transcript Processing
# ---------------------------------------------------------------------------

@server.tool(
    name="search_transcript",
    description="Search an SRT transcript for keywords, concepts, or formulas. Returns exact timestamps, subtitle lines, and surrounding context."
)
def search_transcript(srt_path: str, query: str, context_lines: int = 2) -> List[Dict[str, Any]]:
    """Search for matching query text in a transcript file."""
    return core_search_transcript(srt_path, query, context_lines=context_lines)

@server.tool(
    name="get_transcript",
    description="Retrieve transcript text from an SRT file, either within a timestamp window (e.g. start_time='00:02:00', end_time='00:05:30') or paginated."
)
def get_transcript(
    srt_path: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
) -> Dict[str, Any]:
    """Retrieve formatted subtitles with timestamps."""
    start_sec = parse_time_to_seconds(start_time) if start_time else None
    end_sec = parse_time_to_seconds(end_time) if end_time else None
    return get_transcript_segment(srt_path, start_sec, end_sec, page=page, page_size=page_size)

@server.tool(
    name="get_transcript_summary",
    description="Get high-level summary metrics of a transcript: total duration, subtitle count, word count, and start/end times."
)
def get_transcript_summary(srt_path: str) -> Dict[str, Any]:
    """Get statistics for a transcript."""
    return core_transcript_summary(srt_path)

# ---------------------------------------------------------------------------
# TOOLS: Video & Visual Keyframe Extraction
# ---------------------------------------------------------------------------

@server.tool(
    name="get_video_metadata",
    description="Get video duration, frame rate (fps), resolution (width x height), and total frame count."
)
def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """Get metadata for a video file."""
    return get_video_info(video_path)

@server.tool(
    name="extract_video_keyframes",
    description="Extract visually diverse keyframes from a video using perceptual hashing (pHash) to eliminate duplicate slides or static scenes. Returns image paths and timestamps."
)
def extract_video_keyframes(
    video_path: str,
    output_dir: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_frames: int = 20,
    similarity_threshold: int = 5,
    min_diversity_threshold: int = 10
) -> List[Dict[str, Any]]:
    """Extract diverse keyframes from video."""
    start_sec = parse_time_to_seconds(start_time) if start_time else 0.0
    end_sec = parse_time_to_seconds(end_time) if end_time else None

    return core_extract_keyframes(
        video_path=video_path,
        output_dir=output_dir,
        start_seconds=start_sec,
        end_seconds=end_sec,
        max_frames=max_frames,
        similarity_threshold=similarity_threshold,
        min_diversity_threshold=min_diversity_threshold
    )

@server.tool(
    name="extract_frame_at_timestamp",
    description="Extract a single high-resolution frame from video at an exact timestamp (e.g. '00:04:15' or seconds) and save it to disk."
)
def extract_frame_at_timestamp(
    video_path: str,
    timestamp: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Extract a single frame at a specific timestamp."""
    return core_extract_frame(video_path, timestamp, output_path=output_path)

@server.tool(
    name="create_storyboard",
    description="Extract keyframes and compile them into 3x3 storyboard sheets (9 frames per page with timestamp badges). Ideal for rapid visual inspection by multimodal LLMs."
)
def create_storyboard(
    video_path: str,
    output_dir: Optional[str] = None,
    max_frames: int = 27,
    cell_width: int = 640,
    cell_height: int = 360
) -> Dict[str, Any]:
    """Generate 3x3 storyboard sheets from video."""
    v_stem = Path(video_path).stem
    if not output_dir:
        output_dir = Path("results") / v_stem / "storyboard"
    else:
        output_dir = Path(output_dir)

    frames = core_extract_keyframes(video_path, output_dir=output_dir / "raw_frames", max_frames=max_frames)
    sheets = compile_storyboard_sheets(
        frames=frames,
        output_dir=output_dir,
        title=f"{v_stem} Storyboard",
        cell_w=cell_width,
        cell_h=cell_height
    )

    return {
        "video": video_path,
        "extracted_frames_count": len(frames),
        "total_storyboard_sheets": len(sheets),
        "storyboard_sheets": sheets
    }

# ---------------------------------------------------------------------------
# TOOLS: PDF Slides & Document Processing
# ---------------------------------------------------------------------------

@server.tool(
    name="get_pdf_metadata",
    description="Get metadata, dimensions, and total page count for a PDF file."
)
def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Inspect PDF document."""
    return get_pdf_info(pdf_path)

@server.tool(
    name="extract_pdf_pages",
    description="Extract text and/or render high-resolution slide images from a PDF page range (1-indexed)."
)
def extract_pdf_pages(
    pdf_path: str,
    start_page: int = 1,
    end_page: Optional[int] = None,
    extract_text: bool = True,
    render_images: bool = True,
    output_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Extract text and images from PDF pages."""
    return core_extract_pdf(
        pdf_path=pdf_path,
        start_page=start_page,
        end_page=end_page,
        output_dir=output_dir,
        extract_text=extract_text,
        render_images=render_images
    )

# ---------------------------------------------------------------------------
# TOOLS: Media Downloader
# ---------------------------------------------------------------------------

@server.tool(
    name="download_coursera_lecture",
    description="Download lecture video and subtitles (.srt) from a Coursera lecture URL using an exported cookies file."
)
def download_coursera_lecture(
    url: str,
    output_dir: str = "downloads",
    quality: str = "720p",
    cookies_file: str = "www.coursera.org_cookies.txt"
) -> Dict[str, Any]:
    """Download lecture video and transcript from Coursera."""
    return download_coursera_media(
        url=url,
        cookie_file=cookies_file,
        output_dir=output_dir,
        quality=quality
    )

# ---------------------------------------------------------------------------
# RESOURCES: Direct URI data retrieval
# ---------------------------------------------------------------------------

@server.resource("transcript://{lecture_name}")
def get_transcript_resource(lecture_name: str) -> str:
    """Resource returning the complete text of a lecture transcript."""
    # Find transcript in downloads or results
    target = None
    for pattern in [f"downloads/{lecture_name}.srt", f"results/{lecture_name}/{lecture_name}.srt", f"downloads/{lecture_name}"]:
        p = Path(pattern)
        if p.exists() and p.suffix == ".srt":
            target = p
            break

    if not target:
        matches = list(Path("downloads").glob(f"*{lecture_name}*.srt"))
        if matches:
            target = matches[0]

    if not target or not target.exists():
        return f"Error: No transcript found matching '{lecture_name}'."

    segment = get_transcript_segment(target, page=1, page_size=1000)
    return segment["formatted_text"]

# ---------------------------------------------------------------------------
# Main CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Lore Engine MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport")
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE transport")

    args = parser.parse_args()

    if args.transport == "stdio":
        server.run(transport="stdio")
    elif args.transport == "sse":
        server.run(transport="sse", host=args.host, port=args.port)
    else:
        server.run(transport=args.transport)

if __name__ == "__main__":
    main()
