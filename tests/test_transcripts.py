from pathlib import Path

import pytest

from lore_engine import transcripts

SRT = """1
00:00:01,000 --> 00:00:03,500
Hello there

2
00:00:04,000 --> 00:00:06,000
Second line
with two rows

3
01:02:03,000 --> 01:02:05,000
Late
"""


@pytest.fixture
def srt_file(tmp_path):
    p = tmp_path / "talk.srt"
    p.write_text(SRT, encoding="utf-8")
    return p


def test_parse_srt_formats_times(srt_file):
    subs = transcripts.parse_srt(srt_file)
    assert [s["start_time"] for s in subs] == ["00:00:01", "00:00:04", "01:02:03"]
    assert subs[1]["text"] == "Second line\nwith two rows"
    assert subs[0]["end_seconds"] == 3.5


def test_segment_window_and_pagination(srt_file):
    window = transcripts.get_transcript_segment(srt_file, start_seconds=3.0, end_seconds=5.0)
    assert [s["index"] for s in window["subtitles"]] == [1, 2]
    assert window["formatted_text"].startswith("[00:00:01 - 00:00:03] Hello there")

    page = transcripts.get_transcript_segment(srt_file, page=2, page_size=2)
    assert [s["index"] for s in page["subtitles"]] == [3]
    assert page["total_subtitles"] == 3


def test_summary(srt_file):
    summary = transcripts.get_transcript_summary(srt_file)
    assert summary["total_subtitles"] == 3
    assert summary["duration_formatted"] == "01:02:05"
    assert summary["word_count"] == 8


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        transcripts.parse_srt(Path(tmp_path) / "nope.srt")
