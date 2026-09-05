"""Media downloading module (Coursera + any yt-dlp supported site) for lore-engine.

Two download paths share one public entry point, :func:`download_lecture`:

* **Coursera** lecture pages need the learner's exported browser cookies
  (Netscape ``cookies.txt`` format). The page's ``window.App`` state carries the
  direct MP4 and subtitle URLs, so the download is a plain authenticated GET.
* **Everything else** (YouTube, Vimeo, university media servers, ...) goes
  through ``yt-dlp``, optionally with the same cookies file.

Defaults come from the environment so a caller only has to pass the URL:
``LORE_WORKSPACE_DIR`` (output directory, default ``downloads``) and
``COURSERA_COOKIE_FILE`` (cookies path, default ``www.coursera.org_cookies.txt``
then ``cookies.txt``).
"""

import http.cookiejar
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_WORKSPACE_DIR = "downloads"
DEFAULT_COOKIE_CANDIDATES = ("www.coursera.org_cookies.txt", "cookies.txt")
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def sanitize_filename(name: str) -> str:
    """Sanitize strings for filesystem filenames."""
    return re.sub(r"[\\/*?:\"<>|]", "_", name).strip()


def resolve_workspace_dir(output_dir: str | Path | None = None) -> Path:
    """Pick the output directory: explicit arg > ``LORE_WORKSPACE_DIR`` > ``downloads``."""
    chosen = output_dir or os.getenv("LORE_WORKSPACE_DIR") or DEFAULT_WORKSPACE_DIR
    path = Path(chosen)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_cookie_file(cookie_file: str | Path | None = None, required: bool = False) -> Path | None:
    """Locate a Netscape cookies file: explicit arg > ``COURSERA_COOKIE_FILE`` > defaults.

    Returns ``None`` when nothing exists and ``required`` is False; raises
    ``FileNotFoundError`` naming every candidate when ``required`` is True.
    """
    candidates = []
    if cookie_file:
        candidates.append(Path(cookie_file))
    env_value = os.getenv("COURSERA_COOKIE_FILE")
    if env_value:
        candidates.append(Path(env_value))
    candidates.extend(Path(c) for c in DEFAULT_COOKIE_CANDIDATES)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    if required:
        tried = ", ".join(str(c) for c in candidates)
        raise FileNotFoundError(
            "Coursera cookie file not found (tried: "
            f"{tried}). Export your browser cookies for coursera.org in Netscape "
            "format, or set COURSERA_COOKIE_FILE."
        )
    return None


def is_coursera_url(url: str) -> bool:
    """True for coursera.org lecture/course pages."""
    host = (urlparse(url).hostname or "").lower()
    return host == "coursera.org" or host.endswith(".coursera.org")


def download_file_chunks(url: str, output_path: Path) -> None:
    """Download file in chunks with headers."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req) as response, open(output_path, "wb") as out_file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out_file.write(chunk)


# ---------------------------------------------------------------------------
# Coursera (authenticated page scrape)
# ---------------------------------------------------------------------------


def download_coursera_media(
    url: str,
    cookie_file: str | None = None,
    output_dir: str | None = None,
    sub_lang: str = "en",
    quality: str = "720p",
) -> dict[str, Any]:
    """Download video and subtitles from a Coursera lecture URL using cookies."""
    out_dir = resolve_workspace_dir(output_dir)
    cookie_path = resolve_cookie_file(cookie_file, required=True)

    cj = http.cookiejar.MozillaCookieJar(str(cookie_path))
    cj.load(ignore_discard=True, ignore_expires=True)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

    with opener.open(req) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    idx = html.find("window.App=")
    if idx == -1:
        raise ValueError(
            "Could not find window.App state in page HTML. Ensure the URL is a lecture "
            "page, you are enrolled, and the cookies file is fresh (re-export it if "
            "Coursera logged you out)."
        )

    content = html[idx + len("window.App=") :]
    data, _ = json.JSONDecoder().raw_decode(content)

    stores = data.get("context", {}).get("dispatcher", {}).get("stores", {})
    video_store = stores.get("VideoItemStore", {})
    vdata = video_store.get("videoData", {})

    slug_match = re.search(r"/lecture/[^/]+/([^/?#]+)", url)
    if slug_match:
        clean_title = sanitize_filename(slug_match.group(1).replace("-", "_"))
    else:
        title_match = re.search(r"<title>(.*?)</title>", html)
        raw_title = title_match.group(1).split("|")[0].strip() if title_match else "coursera_lecture"
        clean_title = sanitize_filename(raw_title)

    by_res = vdata.get("sources", {}).get("byResolution", {})
    if not by_res:
        raise ValueError("No video sources found in lecture metadata (not enrolled, or not a video item).")

    chosen_res = quality if quality in by_res else next(iter(by_res))
    video_url = by_res[chosen_res].get("mp4VideoUrl") or by_res[chosen_res].get("webMVideoUrl")
    if not video_url:
        raise ValueError(f"No downloadable stream for quality {chosen_res}.")
    ext = "mp4" if "mp4" in video_url else "webm"
    video_dest = out_dir / f"{clean_title}.{ext}"

    # Subtitles
    subtitles = vdata.get("subtitles", {})
    sub_url_part = subtitles.get(sub_lang) or subtitles.get("en")
    sub_dest = None

    if sub_url_part:
        sub_url = "https://www.coursera.org" + sub_url_part if sub_url_part.startswith("/") else sub_url_part
        sub_dest = out_dir / f"{clean_title}.srt"
        sub_req = urllib.request.Request(sub_url, headers={"User-Agent": _USER_AGENT})
        with opener.open(sub_req) as sub_resp, open(sub_dest, "wb") as f:
            f.write(sub_resp.read())

    download_file_chunks(video_url, video_dest)

    return {
        "source": "coursera",
        "title": clean_title,
        "video_path": str(video_dest.resolve()),
        "srt_path": str(sub_dest.resolve()) if sub_dest else None,
        "quality": chosen_res,
    }


# ---------------------------------------------------------------------------
# Generic sites via yt-dlp
# ---------------------------------------------------------------------------

_VTT_TIMESTAMP = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})|(\d{2}):(\d{2})\.(\d{3})")


def vtt_to_srt(vtt_text: str) -> str:
    """Convert WebVTT subtitle text to SRT without needing ffmpeg."""

    def fix_ts(match: "re.Match[str]") -> str:
        if match.group(1) is not None:
            h, m, s, ms = match.group(1), match.group(2), match.group(3), match.group(4)
        else:
            h, m, s, ms = "00", match.group(5), match.group(6), match.group(7)
        return f"{h}:{m}:{s},{ms}"

    blocks = []
    for raw_block in re.split(r"\n\s*\n", vtt_text.strip().replace("\r\n", "\n")):
        lines = [ln for ln in raw_block.split("\n") if ln.strip()]
        if not lines or lines[0].startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
            continue
        if "-->" not in lines[0] and len(lines) > 1 and "-->" in lines[1]:
            lines = lines[1:]  # drop cue identifier
        if "-->" not in lines[0]:
            continue
        # Keep only "start --> end"; VTT cue settings (position/align) are dropped.
        timing = _VTT_TIMESTAMP.sub(fix_ts, " ".join(lines[0].split()[:3]))
        text = "\n".join(re.sub(r"<[^>]+>", "", ln) for ln in lines[1:]).strip()
        if text:
            blocks.append((timing, text))

    # Collapse consecutive duplicate cues that YouTube auto-captions produce.
    deduped = []
    for timing, text in blocks:
        if deduped and deduped[-1][1] == text:
            continue
        deduped.append((timing, text))

    return "\n".join(f"{i}\n{timing}\n{text}\n" for i, (timing, text) in enumerate(deduped, 1))



def _politeness_opts() -> dict[str, Any]:
    """yt-dlp options that make the downloader look less like a scraper.

    Defaults: small random sleeps between requests/downloads and a rate limit.
    Overrides via env:
      LORE_USER_AGENT           - browser UA to send (match the machine's real browser)
      LORE_YTDLP_OPTS_JSON      - JSON object merged last into the yt-dlp options, e.g.
        {"extractor_args": {"youtubepot-bgutilhttp": {"base_url": ["http://127.0.0.1:4416"]}}}
      LORE_NO_SLEEP=1           - disable the default sleeps (tests)
    """
    import json
    import os

    opts: dict[str, Any] = {}
    if os.environ.get("LORE_NO_SLEEP") != "1":
        opts.update({
            "sleep_interval_requests": 1.0,
            "sleep_interval": 2.0,
            "max_sleep_interval": 6.0,
            "ratelimit": 5_000_000,  # bytes/s
            "retries": 3,
        })
    ua = os.environ.get("LORE_USER_AGENT")
    if ua:
        opts["http_headers"] = {"User-Agent": ua}
    raw = os.environ.get("LORE_YTDLP_OPTS_JSON")
    if raw:
        try:
            extra = json.loads(raw)
            if isinstance(extra, dict):
                opts.update(extra)
        except json.JSONDecodeError:
            pass
    return opts

def download_with_ytdlp(
    url: str,
    output_dir: str | None = None,
    cookie_file: str | None = None,
    sub_lang: str = "en",
    quality: str = "720p",
) -> dict[str, Any]:
    """Download a video plus subtitles from any yt-dlp supported site."""
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ImportError("yt-dlp is required for non-Coursera downloads (pip install yt-dlp).") from exc

    import shutil

    out_dir = resolve_workspace_dir(output_dir)
    height = int(re.sub(r"\D", "", quality) or 720)
    has_ffmpeg = shutil.which("ffmpeg") is not None
    # Without ffmpeg yt-dlp cannot merge separate video/audio streams, so prefer
    # a single progressive MP4 in that case.
    fmt = (
        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]/best"
        if has_ffmpeg
        else f"best[height<={height}][ext=mp4]/best[height<={height}]/best"
    )

    base_opts: dict[str, Any] = {
        "outtmpl": str(out_dir / "%(title).120B-%(id)s.%(ext)s"),
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,  # keep stdout clean: lore.py's last line must be the JSON summary
        "noplaylist": True,
    }
    cookie_path = resolve_cookie_file(cookie_file)
    if cookie_path is not None:
        base_opts["cookiefile"] = str(cookie_path)
    base_opts.update(_politeness_opts())

    # Pass 1: the video itself. Subtitles are deliberately NOT requested here so
    # a subtitle hiccup (YouTube rate-limits the auto-translated tracks) can
    # never take the whole download down with it.
    video_opts = {**base_opts, "format": fmt}
    if has_ffmpeg:
        video_opts["merge_output_format"] = "mp4"
    with yt_dlp.YoutubeDL(video_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:  # playlist guard even with noplaylist
            info = next(e for e in info["entries"] if e)
        video_path = Path(ydl.prepare_filename(info))
        if has_ffmpeg and video_path.suffix.lower() != ".mp4":
            merged = video_path.with_suffix(".mp4")
            if merged.exists():
                video_path = merged

    # Pass 2: one subtitle track (manual if present, else auto-generated) for the
    # requested language only. Best effort: a failure leaves srt_path = None.
    subtitle_error: str | None = None
    sub_opts = {
        **base_opts,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [sub_lang],
        "subtitlesformat": "srt/vtt/best",
    }
    try:
        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.process_ie_result(dict(info), download=True)
    except Exception as exc:  # noqa: BLE001 - subtitles are optional
        subtitle_error = str(exc).splitlines()[-1] if str(exc) else exc.__class__.__name__

    # Locate the subtitle file yt-dlp wrote next to the video and normalise to .srt.
    srt_path: Path | None = None
    stem = video_path.with_suffix("")
    for candidate in sorted(out_dir.glob(f"{stem.name}*.srt")) + sorted(out_dir.glob(f"{stem.name}*.vtt")):
        if candidate.suffix == ".srt":
            srt_path = candidate
            break
        srt_path = stem.with_suffix(".srt")
        srt_path.write_text(
            vtt_to_srt(candidate.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8"
        )
        candidate.unlink(missing_ok=True)
        break

    return {
        "source": "yt-dlp",
        "title": info.get("title") or video_path.stem,
        "video_path": str(video_path.resolve()),
        "srt_path": str(srt_path.resolve()) if srt_path else None,
        "quality": f"{info.get('height') or height}p",
        "duration_seconds": info.get("duration"),
        "subtitle_error": subtitle_error,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def download_lecture(
    url: str,
    output_dir: str | None = None,
    cookie_file: str | None = None,
    sub_lang: str = "en",
    quality: str = "720p",
) -> dict[str, Any]:
    """Download a lecture from any URL: Coursera via cookies, everything else via yt-dlp."""
    if not re.match(r"^https?://", url or ""):
        raise ValueError(f"Expected an http(s) URL, got: {url!r}")
    if is_coursera_url(url):
        return download_coursera_media(
            url, cookie_file=cookie_file, output_dir=output_dir, sub_lang=sub_lang, quality=quality
        )
    return download_with_ytdlp(
        url, output_dir=output_dir, cookie_file=cookie_file, sub_lang=sub_lang, quality=quality
    )
