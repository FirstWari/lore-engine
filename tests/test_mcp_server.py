import pytest
import asyncio
from pathlib import Path
from src.mcp_server.server import server

@pytest.mark.asyncio
async def test_mcp_server_metadata():
    """Verify MCP Server metadata and name."""
    assert server.name == "lore-engine"
    assert server.version == "0.2.0"

@pytest.mark.asyncio
async def test_mcp_tool_registration():
    """Verify all expected MCP tools are registered."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    expected = {
        "list_lectures",
        "search_transcript",
        "get_transcript",
        "get_transcript_summary",
        "get_video_metadata",
        "extract_video_keyframes",
        "extract_frame_at_timestamp",
        "create_storyboard",
        "get_pdf_metadata",
        "extract_pdf_pages",
        "download_coursera_lecture"
    }
    assert expected.issubset(tool_names)

@pytest.mark.asyncio
async def test_list_lectures_tool():
    """Test calling list_lectures."""
    res = await server.call_tool("list_lectures", {})
    assert res is not None
    assert len(res.content) > 0

@pytest.mark.asyncio
async def test_search_transcript_tool():
    """Test searching transcript via MCP."""
    srt_file = Path("downloads/coursera_lecture.srt")
    if srt_file.exists():
        res = await server.call_tool("search_transcript", {
            "srt_path": str(srt_file),
            "query": "volatility"
        })
        assert res is not None
        assert len(res.content) > 0

@pytest.mark.asyncio
async def test_get_transcript_tool():
    """Test retrieving transcript window via MCP."""
    srt_file = Path("downloads/coursera_lecture.srt")
    if srt_file.exists():
        res = await server.call_tool("get_transcript", {
            "srt_path": str(srt_file),
            "start_time": "00:00:10",
            "end_time": "00:00:30"
        })
        assert res is not None
        assert len(res.content) > 0

@pytest.mark.asyncio
async def test_get_video_metadata_tool():
    """Test retrieving video metadata via MCP."""
    video_file = Path("downloads/measuring_max_drawdown.mp4")
    if video_file.exists():
        res = await server.call_tool("get_video_metadata", {
            "video_path": str(video_file)
        })
        assert res is not None
        assert len(res.content) > 0

@pytest.mark.asyncio
async def test_extract_frame_tool():
    """Test single frame extraction via MCP."""
    video_file = Path("downloads/measuring_max_drawdown.mp4")
    if video_file.exists():
        res = await server.call_tool("extract_frame_at_timestamp", {
            "video_path": str(video_file),
            "timestamp": "00:00:05"
        })
        assert res is not None
        assert len(res.content) > 0
