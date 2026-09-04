"""Tests for lore.py, the single-command skill entry point (no network, no video decode)."""

import json
from pathlib import Path

import pytest

import lore


@pytest.fixture
def fake_pipeline(monkeypatch, tmp_path):
    """Stub every heavy core call and record how lore.py wires them together."""
    calls = {}

    def fake_video_info(path):
        calls["video_info"] = str(path)
        return {"duration_seconds": 1234.5, "duration_formatted": "00:20:34", "resolution": "1280x720", "fps": 30.0,
                "video_path": str(path), "total_frames": 37035, "width": 1280, "height": 720}

    def fake_keyframes(path, output_dir=None, max_frames=25, candidate_samples=60, **kw):
        calls["keyframes"] = {"path": str(path), "output_dir": str(output_dir), "max_frames": max_frames,
                              "candidate_samples": candidate_samples}
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        frames = []
        for ts in ("00-00-05", "00-10-00"):
            f = Path(output_dir) / f"frame_{ts}.jpg"
            f.write_bytes(b"jpg")
            frames.append({"timestamp": ts.replace("-", ":"), "seconds": 0, "frame_index": 0, "image_path": str(f)})
        return frames

    def fake_sheets(frames, output_dir, title="", prefix="storyboard", **kw):
        calls["sheets"] = {"n_frames": len(frames), "output_dir": str(output_dir), "prefix": prefix}
        sheet = Path(output_dir) / f"{prefix}_page_01.jpg"
        sheet.write_bytes(b"jpg")
        return [{"page": 1, "total_pages": 1, "frame_count": len(frames), "image_path": str(sheet),
                 "start_time": frames[0]["timestamp"], "end_time": frames[-1]["timestamp"]}]

    monkeypatch.setattr(lore, "get_video_info", fake_video_info)
    monkeypatch.setattr(lore, "extract_keyframes", fake_keyframes)
    monkeypatch.setattr(lore, "compile_storyboard_sheets", fake_sheets)
    return calls


def _make_video(tmp_path, with_srt=True):
    video = tmp_path / "Lecture 1.mp4"
    video.write_bytes(b"mp4")
    if with_srt:
        video.with_suffix(".srt").write_text(
            "1\n00:00:01,000 --> 00:00:03,000\nHello there\n\n2\n00:00:04,000 --> 00:00:06,000\nSecond line\n",
            encoding="utf-8",
        )
    return video


def test_local_video_with_srt_produces_full_folder(fake_pipeline, tmp_path):
    video = _make_video(tmp_path)
    out = tmp_path / "results"

    index = lore.run(str(video), out=str(out), quiet=True)

    target = out / "Lecture 1"
    assert index["kind"] == "video"
    assert Path(index["output_dir"]) == target.resolve()
    assert (target / "transcript.srt").exists()
    txt = (target / "transcript.txt").read_text(encoding="utf-8")
    assert "[00:00:01 - 00:00:03] Hello there" in txt
    assert index["transcript"]["word_count"] == 4
    assert len(index["keyframes"]) == 2
    assert index["storyboard_pages"][0]["image_path"].endswith("storyboard_page_01.jpg")
    assert fake_pipeline["keyframes"]["output_dir"] == str(target / "keyframes")
    # ~10 s per candidate for a 20-minute video, never fewer than 60
    assert fake_pipeline["keyframes"]["candidate_samples"] == 124
    # 2 fake frames < 9 wanted, so the ladder ran to its loosest rung
    assert index["keyframe_thresholds"] == {"similarity": 2, "min_diversity": 4}
    saved = json.loads((target / "index.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Lecture 1"
    assert saved["warnings"] == []


def test_local_video_without_srt_warns_but_completes(fake_pipeline, tmp_path):
    video = _make_video(tmp_path, with_srt=False)
    index = lore.run(str(video), out=str(tmp_path / "r"), quiet=True)
    assert index["transcript_txt"] is None
    assert any("no subtitle" in w for w in index["warnings"])
    assert index["storyboard_pages"]


def test_url_is_downloaded_then_processed(fake_pipeline, tmp_path, monkeypatch):
    video = _make_video(tmp_path)

    def fake_download(url, output_dir=None, cookie_file=None, sub_lang="en", quality="720p"):
        fake_pipeline["download"] = {"url": url, "cookie_file": cookie_file, "sub_lang": sub_lang, "quality": quality}
        return {"source": "yt-dlp", "title": "Zoo", "video_path": str(video),
                "srt_path": str(video.with_suffix(".srt")), "quality": "240p", "subtitle_error": None}

    monkeypatch.setattr(lore, "download_lecture", fake_download)
    index = lore.run("https://www.youtube.com/watch?v=x", out=str(tmp_path / "r"), lang="tr",
                     cookies="c.txt", quality="540p", quiet=True)
    assert fake_pipeline["download"] == {"url": "https://www.youtube.com/watch?v=x", "cookie_file": "c.txt",
                                         "sub_lang": "tr", "quality": "540p"}
    assert index["title"] == "Zoo"
    assert index["source"]["url"] == "https://www.youtube.com/watch?v=x"
    assert index["transcript_txt"]


def test_pdf_path(tmp_path, monkeypatch):
    pdf = tmp_path / "slides.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    def fake_info(path):
        return {"total_pages": 2}

    def fake_extract(path, output_dir=None, extract_text=True, render_images=True, **kw):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        pages = []
        for n in (1, 2):
            img = Path(output_dir) / f"page_{n:03d}.jpg"
            img.write_bytes(b"jpg")
            pages.append({"page_number": n, "text": f"text {n}", "char_count": 6, "image_path": str(img)})
        return pages

    def fake_sheets(frames, output_dir, title="", prefix="storyboard", **kw):
        assert [f["timestamp"] for f in frames] == ["p.1", "p.2"]
        sheet = Path(output_dir) / f"{prefix}_page_01.jpg"
        sheet.write_bytes(b"jpg")
        return [{"page": 1, "image_path": str(sheet)}]

    monkeypatch.setattr(lore, "get_pdf_info", fake_info)
    monkeypatch.setattr(lore, "extract_pdf_content", fake_extract)
    monkeypatch.setattr(lore, "compile_storyboard_sheets", fake_sheets)

    index = lore.run(str(pdf), out=str(tmp_path / "r"), quiet=True)
    assert index["kind"] == "pdf"
    txt = Path(index["transcript_txt"]).read_text(encoding="utf-8")
    assert "[Page 1]\ntext 1" in txt and "[Page 2]\ntext 2" in txt
    assert len(index["pages"]) == 2


def test_main_prints_json_last_line_and_exit_codes(fake_pipeline, tmp_path, capsys):
    video = _make_video(tmp_path)
    rc = lore.main([str(video), "--out", str(tmp_path / "r"), "--json"])
    assert rc == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(last)["title"] == "Lecture 1"

    rc = lore.main([str(tmp_path / "missing.mp4"), "--out", str(tmp_path / "r")])
    assert rc == 1
    err = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert err["error"].startswith("FileNotFoundError")


def test_unsupported_input_is_rejected(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("x")
    with pytest.raises(ValueError):
        lore.run(str(bad), out=str(tmp_path / "r"), quiet=True)


def test_threshold_ladder_stops_at_first_rung_with_enough_frames(tmp_path, monkeypatch):
    attempts = []

    def fake_keyframes(path, output_dir=None, max_frames=25, candidate_samples=60,
                       similarity_threshold=5, min_diversity_threshold=10, **kw):
        attempts.append((similarity_threshold, min_diversity_threshold))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        # strict rung finds 3 frames, the next one finds 12
        n = 3 if similarity_threshold == 10 else 12
        return [{"timestamp": f"00:00:{i:02d}", "seconds": i, "frame_index": i,
                 "image_path": str(Path(output_dir) / f"f{i}.jpg")} for i in range(n)]

    monkeypatch.setattr(lore, "extract_keyframes", fake_keyframes)
    frames, used = lore._select_keyframes(tmp_path / "v.mp4", tmp_path / "kf", 1000.0,
                                          max_frames=27, candidates=170)
    assert attempts == [(10, 16), (5, 10)]
    assert used == (5, 10)
    assert len(frames) == 12


def test_min_useful_frames_scales_with_duration():
    assert lore._min_useful_frames(60, 27) == 9        # short clip: one sheet
    assert lore._min_useful_frames(1728, 27) == 14     # 28 min: one per two minutes
    assert lore._min_useful_frames(36000, 27) == 27    # capped at max_frames
    assert lore._min_useful_frames(1728, 5) == 5
