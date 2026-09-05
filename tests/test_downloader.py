"""Unit tests for lore_engine.downloader and friends (no network)."""

import json
import os

import pytest

from lore_engine import cdp_fetch, downloader, html2md, textsafe


class TestRouting:
    def test_coursera_url_detection(self):
        assert downloader.is_coursera_url("https://www.coursera.org/learn/x/lecture/abc/intro")
        assert downloader.is_coursera_url("https://coursera.org/learn/x")
        assert not downloader.is_coursera_url("https://www.youtube.com/watch?v=abc")
        assert not downloader.is_coursera_url("https://notcoursera.org/learn/x")
        assert not downloader.is_coursera_url("https://coursera.org.evil.com/learn/x")

    def test_youtube_url_detection(self):
        assert downloader.is_youtube_url("https://www.youtube.com/watch?v=abc")
        assert downloader.is_youtube_url("https://youtu.be/abc")
        assert not downloader.is_youtube_url("https://vimeo.com/1")

    def test_coursera_item_kind(self):
        assert downloader.coursera_item_kind("https://www.coursera.org/learn/c/lecture/i/t") == "lecture"
        assert downloader.coursera_item_kind("https://www.coursera.org/learn/c/supplement/i/t") == "reading"
        assert downloader.coursera_item_kind("https://www.coursera.org/learn/c/quiz/i/t") == "other"
        assert downloader.coursera_item_kind("https://www.coursera.org/learn/c/ungradedLti/i/t") == "reading"

    def test_download_lecture_routes_coursera(self, monkeypatch):
        calls = {}
        monkeypatch.setattr(downloader, "download_coursera_media", lambda url, **kw: calls.setdefault("coursera", (url, kw)))
        monkeypatch.setattr(downloader, "download_with_ytdlp", lambda url, **kw: calls.setdefault("ytdlp", (url, kw)))
        downloader.download_lecture("https://www.coursera.org/learn/c/lecture/i/t", quality="540p")
        assert "coursera" in calls and "ytdlp" not in calls
        assert calls["coursera"][1]["quality"] == "540p"

    def test_download_lecture_routes_other_sites_to_ytdlp(self, monkeypatch):
        calls = {}
        monkeypatch.setattr(downloader, "download_coursera_media", lambda url, **kw: calls.setdefault("coursera", url))
        monkeypatch.setattr(downloader, "download_with_ytdlp", lambda url, **kw: calls.setdefault("ytdlp", url))
        downloader.download_lecture("https://www.youtube.com/watch?v=jNQXAC9IVRw")
        assert calls == {"ytdlp": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}

    def test_download_lecture_rejects_non_url(self):
        with pytest.raises(ValueError):
            downloader.download_lecture("lecture.mp4")


class TestWorkspace:
    def test_workspace_dir_from_env(self, tmp_path, monkeypatch):
        target = tmp_path / "ws"
        monkeypatch.setenv("LORE_WORKSPACE_DIR", str(target))
        assert downloader.resolve_workspace_dir() == target
        assert target.is_dir()

    def test_explicit_workspace_dir_wins_over_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LORE_WORKSPACE_DIR", str(tmp_path / "env"))
        explicit = tmp_path / "explicit"
        assert downloader.resolve_workspace_dir(explicit) == explicit


class TestCookiePolicy:
    YT = "https://www.youtube.com/watch?v=abc"

    def test_no_cookies_by_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("LORE_YT_COOKIES", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "cookies.txt").write_text("# would have been picked up by the old code\n")
        assert downloader.youtube_cookie_file(None, self.YT) is None

    def test_cookies_only_for_youtube(self, monkeypatch, tmp_path):
        f = tmp_path / "yt.txt"
        f.write_text("# Netscape HTTP Cookie File\n")
        if os.name != "nt":
            f.chmod(0o600)
        monkeypatch.setenv("LORE_YT_COOKIES", str(f))
        assert downloader.youtube_cookie_file(None, self.YT) == f
        assert downloader.youtube_cookie_file(None, "https://vimeo.com/1") is None
        assert downloader.youtube_cookie_file(None, "https://www.coursera.org/learn/x") is None

    def test_cookie_path_must_be_absolute_and_exist(self, monkeypatch, tmp_path):
        with pytest.raises(ValueError):
            downloader.youtube_cookie_file("relative/cookies.txt", self.YT)
        with pytest.raises(FileNotFoundError):
            downloader.youtube_cookie_file(str(tmp_path / "missing.txt"), self.YT)

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
    def test_cookie_file_must_be_private(self, tmp_path):
        f = tmp_path / "yt.txt"
        f.write_text("#\n")
        f.chmod(0o644)
        with pytest.raises(PermissionError):
            downloader.youtube_cookie_file(str(f), self.YT)


class TestYtdlpOptions:
    YT = "https://www.youtube.com/watch?v=abc"

    def test_opts_json_hook_is_gone(self, monkeypatch):
        monkeypatch.setenv("LORE_YTDLP_OPTS_JSON", json.dumps({"postprocessors": [{"key": "Exec", "exec_cmd": "id"}]}))
        opts = downloader.ytdlp_options(self.YT, cookie_file=None)
        assert "postprocessors" not in opts and "exec_cmd" not in json.dumps(opts)

    def test_allowlisted_env(self, monkeypatch):
        monkeypatch.setenv("LORE_POT_BASE_URL", "http://127.0.0.1:4416/")
        monkeypatch.setenv("LORE_YT_PLAYER_CLIENTS", "web,default")
        monkeypatch.setenv("LORE_USER_AGENT", "UA/1.0")
        monkeypatch.setenv("LORE_NO_SLEEP", "1")
        opts = downloader.ytdlp_options(self.YT, cookie_file=None)
        assert opts["extractor_args"]["youtubepot-bgutilhttp"]["base_url"] == ["http://127.0.0.1:4416"]
        assert opts["extractor_args"]["youtube"]["player_client"] == ["web", "default"]
        assert opts["http_headers"]["User-Agent"] == "UA/1.0"
        assert opts["retries"] == 3 and opts["socket_timeout"] == 30 and "sleep_interval" not in opts
        assert opts["remote_components"] == ["ejs:github"]

    def test_bad_env_values_are_ignored(self, monkeypatch):
        monkeypatch.setenv("LORE_POT_BASE_URL", "http://evil.example/pot")
        monkeypatch.setenv("LORE_YT_PLAYER_CLIENTS", "web;rm -rf /")
        monkeypatch.setenv("LORE_IMPERSONATE", "chrome; id")
        opts = downloader.ytdlp_options(self.YT, cookie_file=None)
        assert "extractor_args" not in opts and "impersonate" not in opts

    def test_sleeps_on_by_default(self, monkeypatch):
        monkeypatch.delenv("LORE_NO_SLEEP", raising=False)
        opts = downloader.ytdlp_options(self.YT, cookie_file=None)
        assert opts["sleep_interval_requests"] == 1.0 and opts["ratelimit"] == 5_000_000 and opts["noplaylist"]


class TestDailyCap:
    def test_cap_counts_and_blocks(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LORE_STATE_DIR", str(tmp_path))
        monkeypatch.setenv("LORE_YT_DAILY_MAX", "2")
        url = "https://www.youtube.com/watch?v=abc"
        downloader._daily_cap_check(url)
        downloader._daily_cap_check(url)
        with pytest.raises(RuntimeError, match="YT_DAILY_CAP"):
            downloader._daily_cap_check(url)
        downloader._daily_cap_check("https://vimeo.com/1")  # not counted

    def test_cap_zero_is_unlimited(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LORE_STATE_DIR", str(tmp_path))
        monkeypatch.setenv("LORE_YT_DAILY_MAX", "0")
        for _ in range(5):
            downloader._daily_cap_check("https://youtu.be/x")


class TestLanguage:
    def test_youtube_language_preference_order(self):
        info = {"language": "tr", "subtitles": {"en": []}, "automatic_captions": {"tr-orig": [], "en": []}}
        assert downloader.pick_youtube_language(info) == ["tr", "tr-orig"]
        info2 = {"automatic_captions": {"en": [], "de-orig": []}}
        assert downloader.pick_youtube_language(info2) == ["de", "de-orig"]
        info3 = {"subtitles": {"fr": []}}
        assert downloader.pick_youtube_language(info3) == ["fr", "fr-orig"]
        assert downloader.pick_youtube_language({}) == ["en", "en-orig"]
        assert downloader.pick_youtube_language(info, "en")[0] == "en"

    def test_coursera_pick_language(self):
        assert cdp_fetch.pick_language("auto", ["en", "tr"], ["tr"]) == "tr"
        assert cdp_fetch.pick_language("auto", ["en", "es"], []) == "en"
        assert cdp_fetch.pick_language("tr", ["en", "tr-TR"], []) == "tr-TR"
        assert cdp_fetch.pick_language("auto", ["es"], []) == "es"
        assert cdp_fetch.pick_language("auto", [], ["en"]) is None


class TestUrlAllowlist:
    def test_cdn_allowlist(self):
        ok = downloader._check_download_url("https://d3c33hcgiwev3.cloudfront.net/x.mp4?Signature=1", allowed_suffixes=downloader.CDN_HOST_SUFFIXES)
        assert ok.startswith("https://")
        for bad in ("http://d3c33hcgiwev3.cloudfront.net/x.mp4", "file:///etc/passwd", "https://evil.example/x.mp4", "https://cloudfront.net.evil.com/x"):
            with pytest.raises(ValueError):
                downloader._check_download_url(bad, allowed_suffixes=downloader.CDN_HOST_SUFFIXES)


class TestTextSafe:
    def test_sanitize_filename_traversal_and_controls(self):
        s = textsafe.sanitize_filename
        assert s("..") == "untitled" and s(".") == "untitled" and s("") == "untitled" and s("   ") == "untitled"
        assert "/" not in s("a/b\\c") and s("a/b\\c") == "a_b_c"
        assert s("evil\x1b[31mred\x00") == "evilred"  # whole ANSI sequence and NUL removed
        assert s("CON") == "_CON" and s("nul.txt") == "_nul.txt"
        assert s("name...") == "name"
        assert len(s("x" * 500)) <= textsafe.MAX_NAME_LEN
        assert "‮" not in s("abc‮def")

    def test_clean_text(self):
        assert textsafe.clean_text("a\x1b[0mb​c\n") == "ab" + "c\n"
        assert textsafe.clean_text("<b>x</b> y", strip_tags=True) == "x y"

    def test_safe_console(self):
        out = textsafe.safe_console("line1\nline2\x07" + "z" * 400)
        assert "\n" not in out and "\x07" not in out and len(out) <= 300

    def test_safe_id(self):
        assert textsafe.safe_id("intro-to ML!/x") == "intro-to-ML-x"
        assert textsafe.safe_id("") == "item"


class TestHtml2Md:
    def test_basic_structure(self):
        html = "<h2>Title</h2><p>Hello <b>world</b> <a href='https://x.y/z'>link</a></p><ul><li>a</li><li>b</li></ul><pre><code>x = 1</code></pre><script>evil()</script>"
        md = html2md.html_to_markdown(html)
        assert "## Title" in md and "**world**" in md and "[link](https://x.y/z)" in md
        assert "- a" in md and "- b" in md and "```\nx = 1" in md and "evil" not in md


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
