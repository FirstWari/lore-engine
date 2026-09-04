"""Unit tests for src.core.downloader (no network)."""

import pytest

from src.core import downloader


class TestRouting:
    def test_coursera_url_detection(self):
        assert downloader.is_coursera_url("https://www.coursera.org/learn/x/lecture/abc/intro")
        assert downloader.is_coursera_url("https://coursera.org/learn/x")
        assert not downloader.is_coursera_url("https://www.youtube.com/watch?v=abc")
        assert not downloader.is_coursera_url("https://notcoursera.org/learn/x")

    def test_download_lecture_routes_coursera(self, monkeypatch):
        calls = {}
        monkeypatch.setattr(downloader, "download_coursera_media",
                            lambda url, **kw: calls.setdefault("coursera", (url, kw)))
        monkeypatch.setattr(downloader, "download_with_ytdlp",
                            lambda url, **kw: calls.setdefault("ytdlp", (url, kw)))
        downloader.download_lecture("https://www.coursera.org/learn/c/lecture/i/t", quality="540p")
        assert "coursera" in calls and "ytdlp" not in calls
        assert calls["coursera"][1]["quality"] == "540p"

    def test_download_lecture_routes_other_sites_to_ytdlp(self, monkeypatch):
        calls = {}
        monkeypatch.setattr(downloader, "download_coursera_media",
                            lambda url, **kw: calls.setdefault("coursera", url))
        monkeypatch.setattr(downloader, "download_with_ytdlp",
                            lambda url, **kw: calls.setdefault("ytdlp", url))
        downloader.download_lecture("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        assert calls == {"ytdlp": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}

    def test_download_lecture_rejects_non_url(self):
        with pytest.raises(ValueError):
            downloader.download_lecture("lecture.mp4")


class TestDefaults:
    def test_workspace_dir_from_env(self, tmp_path, monkeypatch):
        target = tmp_path / "ws"
        monkeypatch.setenv("LORE_WORKSPACE_DIR", str(target))
        assert downloader.resolve_workspace_dir() == target
        assert target.is_dir()

    def test_explicit_workspace_dir_wins_over_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LORE_WORKSPACE_DIR", str(tmp_path / "env"))
        explicit = tmp_path / "explicit"
        assert downloader.resolve_workspace_dir(explicit) == explicit

    def test_cookie_file_from_env(self, tmp_path, monkeypatch):
        cookie = tmp_path / "my_cookies.txt"
        cookie.write_text("# Netscape HTTP Cookie File\n")
        monkeypatch.setenv("COURSERA_COOKIE_FILE", str(cookie))
        monkeypatch.chdir(tmp_path)
        assert downloader.resolve_cookie_file() == cookie

    def test_cookie_file_missing_is_optional_unless_required(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COURSERA_COOKIE_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        assert downloader.resolve_cookie_file() is None
        with pytest.raises(FileNotFoundError):
            downloader.resolve_cookie_file(required=True)


class TestVttToSrt:
    def test_converts_timestamps_and_numbers_cues(self):
        vtt = (
            "WEBVTT\nKind: captions\nLanguage: en\n\n"
            "00:00:01.000 --> 00:00:03.500 align:start position:0%\nHello <c>world</c>\n\n"
            "00:05.000 --> 00:07.250\nSecond line\n"
        )
        srt = downloader.vtt_to_srt(vtt)
        assert srt.startswith("1\n00:00:01,000 --> 00:00:03,500\nHello world\n")
        assert "2\n00:00:05,000 --> 00:00:07,250\nSecond line\n" in srt

    def test_drops_duplicate_consecutive_cues(self):
        vtt = (
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nsame\n\n"
            "00:00:02.000 --> 00:00:03.000\nsame\n\n00:00:03.000 --> 00:00:04.000\nnext\n"
        )
        srt = downloader.vtt_to_srt(vtt)
        assert srt.count("same") == 1
        assert "next" in srt
