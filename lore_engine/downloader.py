"""Media downloading for lore-engine: Coursera through the real browser, everything else via yt-dlp.

Design rules (see SKILL.md "Security"):

* **Coursera**: the lecture/reading page and the subtitle file are read through the
  user's logged-in Chromium over CDP (:mod:`lore_engine.cdp_fetch`). Python never sends
  Coursera cookies; only the signed CDN media URL is downloaded from Python.
* **yt-dlp** (YouTube & co.): options come from a small allowlist of environment
  variables — there is no generic "options JSON" hook. Cookies are used only when
  ``LORE_YT_COOKIES`` points at an existing, private (0600) Netscape file, and only for
  YouTube URLs. A daily download cap protects the account.
* All remote-derived strings go through :mod:`lore_engine.textsafe` before they become
  paths or output.

Environment:
    LORE_WORKSPACE_DIR   where media lands (default ``downloads``)
    LORE_USER_AGENT      UA for CDN downloads and yt-dlp (should match the browser)
    LORE_YT_COOKIES      YouTube-only Netscape cookie file (0600). Optional.
    LORE_POT_BASE_URL    bgutil PO-token provider (e.g. http://127.0.0.1:4416). Optional.
    LORE_YT_PLAYER_CLIENTS  comma list, ``[a-z_,]`` only (e.g. ``web,default``). Optional.
    LORE_IMPERSONATE     yt-dlp impersonation target (``chrome``, ``chrome-136``). Optional.
    LORE_YT_DAILY_MAX    max YouTube downloads per day (default 12; 0 = unlimited)
    LORE_MAX_MEDIA_MB    refuse media larger than this (default 2048)
    LORE_STATE_DIR       counters (default ``<workspace>/.state``)
    LORE_NO_SLEEP=1      disable the polite sleeps (tests)
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import stat
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .textsafe import clean_text, safe_id, sanitize_filename

DEFAULT_WORKSPACE_DIR = "downloads"
YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com", "google.com")
CDN_HOST_SUFFIXES = (".cloudfront.net", ".coursera.org", "coursera.org", ".coursera-assets.org", "coursera-assets.org")
_PLAYER_CLIENTS_RE = re.compile(r"^[a-z_]+(,[a-z_]+)*$")
_IMPERSONATE_RE = re.compile(r"^[a-z]+(-\d+)?(:[a-z0-9.-]+)?$")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def resolve_workspace_dir(output_dir: str | Path | None = None) -> Path:
    """Pick the output directory: explicit arg > ``LORE_WORKSPACE_DIR`` > ``downloads``."""
    chosen = output_dir or os.getenv("LORE_WORKSPACE_DIR") or DEFAULT_WORKSPACE_DIR
    path = Path(chosen)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_dir() -> Path:
    p = Path(os.getenv("LORE_STATE_DIR") or (resolve_workspace_dir() / ".state"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _user_agent() -> str | None:
    ua = os.getenv("LORE_USER_AGENT", "").strip()
    return ua or None


def _max_media_bytes() -> int:
    try:
        mb = int(os.getenv("LORE_MAX_MEDIA_MB", "2048"))
    except ValueError:
        mb = 2048
    return max(1, mb) * 1024 * 1024


def is_coursera_url(url: str) -> bool:
    """True for coursera.org lecture/course pages."""
    host = (urlparse(url).hostname or "").lower()
    return host == "coursera.org" or host.endswith(".coursera.org")


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ("youtube.com", "youtu.be", "youtube-nocookie.com"))


def coursera_item_kind(url: str) -> str:
    """'lecture' | 'reading' | 'other' from the URL path."""
    path = urlparse(url).path.lower()
    if "/lecture/" in path:
        return "lecture"
    if "/supplement/" in path or "/reading/" in path or "/ungradedWidget/".lower() in path:
        return "reading"
    return "other"


def _check_download_url(url: str, *, allowed_suffixes: tuple[str, ...]) -> str:
    """Only https to an allow-listed host may be downloaded from Python."""
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not host:
        raise ValueError(f"refusing non-https download URL: {url[:80]!r}")
    if not any(host == s.lstrip(".") or host.endswith(s if s.startswith(".") else "." + s) for s in allowed_suffixes):
        raise ValueError(f"refusing download from unexpected host: {host}")
    return url


def download_file_chunks(url: str, output_path: Path, *, timeout: float = 60.0, max_bytes: int | None = None) -> int:
    """Stream a URL to disk with a size cap. Returns bytes written."""
    max_bytes = max_bytes or _max_media_bytes()
    headers = {"User-Agent": _user_agent()} if _user_agent() else {}
    req = urllib.request.Request(url, headers=headers)
    written = 0
    with urllib.request.urlopen(req, timeout=timeout) as response, open(output_path, "wb") as out_file:
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError(f"media too large ({int(length) // (1024 * 1024)} MB > cap)")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                raise ValueError("media exceeded size cap during download")
            out_file.write(chunk)
    return written


# ---------------------------------------------------------------------------
# Coursera (real browser reads the page; Python fetches only the CDN media)
# ---------------------------------------------------------------------------


def download_coursera_media(
    url: str,
    cookie_file: str | None = None,  # ignored: kept for call compatibility
    output_dir: str | None = None,
    sub_lang: str = "auto",
    quality: str = "720p",
) -> dict[str, Any]:
    """Coursera lecture (video + subtitles) or reading (markdown + assets) via the logged-in browser."""
    from . import cdp_fetch  # local import: websockets is optional

    out_dir = resolve_workspace_dir(output_dir)
    url_kind = coursera_item_kind(url)
    if url_kind == "other":
        raise ValueError("Unsupported Coursera URL: give a /lecture/ (video) or /supplement/ (reading) item page.")
    page = cdp_fetch.fetch_coursera_page(url, sub_lang=sub_lang)
    if url_kind == "lecture" and page["kind"] != "lecture":
        raise cdp_fetch.CourseraPageError("lecture page has no video data (not enrolled, or page format changed)")
    if url_kind == "reading":
        page["kind"] = "reading" if page.get("reading_html") else "other"
    slug_match = re.search(r"/(?:lecture|supplement|reading)/[^/]+/([^/?#]+)", url)
    item_id = safe_id(slug_match.group(1) if slug_match else urlparse(url).path.rsplit("/", 1)[-1])
    title = clean_text(page.get("title") or "").split("|")[0].strip() or item_id
    clean_title = sanitize_filename(title)

    result: dict[str, Any] = {
        "source": "coursera",
        "kind": page["kind"],
        "title": clean_title,
        "item_id": item_id,
        "language": page.get("subtitle_lang"),
        "languages": page.get("languages") or [],
        "assets": [],
        "subtitle_error": page.get("subtitle_error"),
    }

    if page["kind"] == "lecture":
        vdata = page["video"] or {}
        by_res = (vdata.get("sources") or {}).get("byResolution") or {}
        if not by_res:
            raise ValueError("No video sources found in lecture metadata (not enrolled, or not a video item).")
        chosen_res = quality if quality in by_res else sorted(by_res, key=lambda r: int(re.sub(r"\D", "", r) or 0))[-1]
        entry = by_res[chosen_res] or {}
        video_url = entry.get("mp4VideoUrl") or entry.get("webMVideoUrl")
        if not video_url:
            raise ValueError(f"No downloadable stream for quality {chosen_res}.")
        _check_download_url(video_url, allowed_suffixes=CDN_HOST_SUFFIXES)
        ext = "mp4" if "mp4" in urlparse(video_url).path.lower() else "webm"
        video_dest = out_dir / f"{clean_title}-{item_id}.{ext}"
        download_file_chunks(video_url, video_dest)
        srt_dest = None
        if page.get("subtitle_text"):
            text = clean_text(page["subtitle_text"])
            if "WEBVTT" in text[:20]:
                text = vtt_to_srt(text)
            srt_dest = out_dir / f"{clean_title}-{item_id}.srt"
            srt_dest.write_text(text, encoding="utf-8")
        result.update({
            "video_path": str(video_dest.resolve()),
            "srt_path": str(srt_dest.resolve()) if srt_dest else None,
            "quality": chosen_res,
        })
    elif page["kind"] == "reading":
        from .html2md import html_to_markdown

        md = clean_text(html_to_markdown(page.get("reading_html") or ""), strip_tags=False)
        md_dest = out_dir / f"{clean_title}-{item_id}.reading.md"
        md_dest.write_text(f"# {title}\n\nSource: {page.get('url') or url}\n\n{md}", encoding="utf-8")
        result.update({"video_path": None, "srt_path": None, "reading_md": str(md_dest.resolve())})
    else:
        raise ValueError("Unsupported Coursera item (not a /lecture/ or /supplement/ page).")

    # downloadable course files (slides, notebooks, PDFs) — only from Coursera CDNs, capped
    assets_dir = out_dir / f"{clean_title}-{item_id}.assets"
    for asset in page.get("assets") or []:
        try:
            a_url = _check_download_url(asset.get("url") or "", allowed_suffixes=CDN_HOST_SUFFIXES)
        except ValueError:
            continue
        name = sanitize_filename(asset.get("name") or Path(urlparse(a_url).path).name or "asset")
        if not Path(name).suffix:
            name += Path(urlparse(a_url).path).suffix or ".bin"
        assets_dir.mkdir(parents=True, exist_ok=True)
        dest = assets_dir / name
        try:
            size = download_file_chunks(a_url, dest, max_bytes=200 * 1024 * 1024)
            result["assets"].append({"name": name, "path": str(dest.resolve()), "bytes": size})
        except Exception as exc:  # noqa: BLE001 - assets are optional
            result.setdefault("asset_errors", []).append(f"{name}: {exc.__class__.__name__}")
    return result


# ---------------------------------------------------------------------------
# yt-dlp (YouTube and other sites)
# ---------------------------------------------------------------------------

_VTT_TIMESTAMP = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})|(\d{2}):(\d{2})\.(\d{3})")


def vtt_to_srt(vtt_text: str) -> str:
    """Convert WebVTT subtitle text to SRT without needing ffmpeg."""

    def fix_ts(match: re.Match[str]) -> str:
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
        timing = _VTT_TIMESTAMP.sub(fix_ts, " ".join(lines[0].split()[:3]))
        text = "\n".join(re.sub(r"<[^>]+>", "", ln) for ln in lines[1:]).strip()
        if text:
            blocks.append((timing, text))

    deduped = []
    for timing, text in blocks:
        if deduped and deduped[-1][1] == text:
            continue
        deduped.append((timing, text))

    return "\n".join(f"{i}\n{timing}\n{text}\n" for i, (timing, text) in enumerate(deduped, 1))


def youtube_cookie_file(explicit: str | None, url: str) -> Path | None:
    """The only way cookies reach yt-dlp: explicit path or LORE_YT_COOKIES, YouTube URLs only,
    file must exist, be a regular file and be private (no group/other permissions on POSIX)."""
    raw = explicit or os.getenv("LORE_YT_COOKIES")
    if not raw:
        return None
    if not is_youtube_url(url):
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        raise ValueError("LORE_YT_COOKIES / --cookies must be an absolute path")
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {p}")
    if os.name != "nt":
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode & 0o077:
            raise PermissionError(f"cookie file {p} must be private (chmod 600), has {oct(mode)}")
    return p


def _daily_cap_check(url: str) -> None:
    """Count YouTube downloads per UTC day; raise when the cap is reached."""
    if not is_youtube_url(url):
        return
    try:
        cap = int(os.getenv("LORE_YT_DAILY_MAX", "12"))
    except ValueError:
        cap = 12
    if cap <= 0:
        return
    f = _state_dir() / "yt-daily.json"
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        data = {}
    count = int(data.get(today, 0))
    if count >= cap:
        raise RuntimeError(f"YT_DAILY_CAP: {count}/{cap} YouTube downloads already made today (UTC); try tomorrow")
    data = {today: count + 1}
    f.write_text(json.dumps(data), encoding="utf-8")


def ytdlp_options(url: str, *, cookie_file: Path | None) -> dict[str, Any]:
    """Allow-listed yt-dlp options. Nothing here can run a program or redirect files."""
    opts: dict[str, Any] = {
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "noplaylist": True,
        "max_filesize": _max_media_bytes(),
    }
    if os.getenv("LORE_NO_SLEEP") != "1":
        opts.update({"sleep_interval_requests": 1.0, "sleep_interval": 2.0, "max_sleep_interval": 6.0,
                     "ratelimit": 5_000_000})
    ua = _user_agent()
    if ua:
        opts["http_headers"] = {"User-Agent": ua}
    if cookie_file is not None:
        opts["cookiefile"] = str(cookie_file)
    extractor_args: dict[str, dict[str, list[str]]] = {}
    pot = os.getenv("LORE_POT_BASE_URL", "").strip()
    if pot and re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?/?$", pot):
        extractor_args["youtubepot-bgutilhttp"] = {"base_url": [pot.rstrip("/")]}
    clients = os.getenv("LORE_YT_PLAYER_CLIENTS", "").strip()
    if clients and _PLAYER_CLIENTS_RE.match(clients):
        extractor_args["youtube"] = {"player_client": clients.split(",")}
    if extractor_args:
        opts["extractor_args"] = extractor_args
    imp = os.getenv("LORE_IMPERSONATE", "").strip()
    if imp and _IMPERSONATE_RE.match(imp):
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget

            opts["impersonate"] = ImpersonateTarget.from_str(imp)
        except Exception:  # noqa: BLE001 - curl_cffi missing or bad target: run without
            pass
    return opts


def pick_youtube_language(info: dict[str, Any], preferred: str = "auto") -> list[str]:
    """Subtitle languages to request: explicit > original language (info['language'] or '<x>-orig')
    > first manual subtitle > 'en'. Returns the list yt-dlp expects (original first, '-orig' variant next)."""
    manual = list((info.get("subtitles") or {}).keys())
    auto = list((info.get("automatic_captions") or {}).keys())
    if preferred and preferred.lower() != "auto":
        base = preferred.split("-")[0]
        return [preferred, f"{base}-orig", base]
    orig = info.get("language")
    if not orig:
        for key in auto:
            if key.endswith("-orig"):
                orig = key[: -len("-orig")]
                break
    if not orig and manual:
        orig = manual[0]
    orig = (orig or "en").split("-")[0]
    return [orig, f"{orig}-orig"]


def download_with_ytdlp(
    url: str,
    output_dir: str | None = None,
    cookie_file: str | None = None,
    sub_lang: str = "auto",
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
    fmt = (
        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]/best"
        if has_ffmpeg
        else f"best[height<={height}][ext=mp4]/best[height<={height}]/best"
    )
    cookies = youtube_cookie_file(cookie_file, url)
    _daily_cap_check(url)

    base_opts: dict[str, Any] = {
        "outtmpl": str(out_dir / "%(title).120B-%(id)s.%(ext)s"),
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,  # keep stdout clean: lore.py's last line must be the JSON summary
        **ytdlp_options(url, cookie_file=cookies),
    }

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

    langs = pick_youtube_language(info, sub_lang)
    subtitle_error: str | None = None
    sub_opts = {
        **base_opts,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": langs,
        "subtitlesformat": "srt/vtt/best",
    }
    try:
        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.process_ie_result(dict(info), download=True)
    except Exception as exc:  # noqa: BLE001 - subtitles are optional
        subtitle_error = clean_text(str(exc).splitlines()[-1] if str(exc) else exc.__class__.__name__)[:200]

    if cookies is not None and os.name != "nt":
        try:
            os.chmod(cookies, 0o600)  # yt-dlp rewrites the jar; keep it private
        except OSError:
            pass

    srt_path: Path | None = None
    stem = video_path.with_suffix("")
    for candidate in sorted(out_dir.glob(f"{stem.name}*.srt")) + sorted(out_dir.glob(f"{stem.name}*.vtt")):
        if candidate.suffix == ".srt":
            srt_path = candidate
            break
        srt_path = stem.with_suffix(".srt")
        srt_path.write_text(vtt_to_srt(candidate.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
        candidate.unlink(missing_ok=True)
        break

    return {
        "source": "yt-dlp",
        "kind": "lecture",
        "title": sanitize_filename(clean_text(info.get("title") or video_path.stem)),
        "item_id": safe_id(str(info.get("id") or video_path.stem)),
        "video_path": str(video_path.resolve()),
        "srt_path": str(srt_path.resolve()) if srt_path else None,
        "quality": f"{info.get('height') or height}p",
        "duration_seconds": info.get("duration"),
        "language": langs[0],
        "subtitle_error": subtitle_error,
        "used_cookies": cookies is not None,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def download_lecture(
    url: str,
    output_dir: str | None = None,
    cookie_file: str | None = None,
    sub_lang: str = "auto",
    quality: str = "720p",
) -> dict[str, Any]:
    """Download a lecture from any URL: Coursera via the browser, everything else via yt-dlp."""
    if not re.match(r"^https?://", url or ""):
        raise ValueError(f"Expected an http(s) URL, got: {url!r}")
    if is_coursera_url(url):
        return download_coursera_media(url, cookie_file=cookie_file, output_dir=output_dir, sub_lang=sub_lang, quality=quality)
    return download_with_ytdlp(url, output_dir=output_dir, cookie_file=cookie_file, sub_lang=sub_lang, quality=quality)
