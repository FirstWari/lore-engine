"""Media downloading module (Coursera + Web) for lore-engine."""

import re
import json
import http.cookiejar
import urllib.request
from pathlib import Path
from typing import Dict, Any

def sanitize_filename(name: str) -> str:
    """Sanitize strings for filesystem filenames."""
    return re.sub(r"[\\/*?:\"<>|]", "_", name).strip()

def download_file_chunks(url: str, output_path: Path) -> None:
    """Download file in chunks with headers."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req) as response, open(output_path, "wb") as out_file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out_file.write(chunk)

def download_coursera_media(
    url: str,
    cookie_file: str = "www.coursera.org_cookies.txt",
    output_dir: str = "downloads",
    sub_lang: str = "en",
    quality: str = "720p"
) -> Dict[str, Any]:
    """Download video and subtitles from a Coursera lecture URL using cookies."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cookie_path = Path(cookie_file)
    if not cookie_path.exists():
        alt_path = Path("cookies.txt")
        if alt_path.exists():
            cookie_path = alt_path
        else:
            raise FileNotFoundError(f"Coursera cookie file not found: {cookie_file} or cookies.txt")

    cj = http.cookiejar.MozillaCookieJar(str(cookie_path))
    cj.load(ignore_discard=True, ignore_expires=True)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    with opener.open(req) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    idx = html.find("window.App=")
    if idx == -1:
        raise ValueError("Could not find window.App state in page HTML. Ensure URL is valid and you are enrolled.")

    content = html[idx + len("window.App="):]
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
        raise ValueError("No video sources found in lecture metadata.")

    chosen_res = quality if quality in by_res else (list(by_res.keys())[0] if by_res else None)
    video_url = by_res[chosen_res].get("mp4VideoUrl") or by_res[chosen_res].get("webMVideoUrl")
    ext = "mp4" if "mp4" in (video_url or "") else "webm"
    video_dest = out_dir / f"{clean_title}.{ext}"

    # Subtitles
    subtitles = vdata.get("subtitles", {})
    sub_url_part = subtitles.get(sub_lang) or subtitles.get("en")
    sub_dest = None

    if sub_url_part:
        if sub_url_part.startswith("/"):
            sub_url = "https://www.coursera.org" + sub_url_part
        else:
            sub_url = sub_url_part
        sub_dest = out_dir / f"{clean_title}.srt"
        sub_req = urllib.request.Request(
            sub_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with opener.open(sub_req) as sub_resp, open(sub_dest, "wb") as f:
            f.write(sub_resp.read())

    download_file_chunks(video_url, video_dest)

    return {
        "title": clean_title,
        "video_path": str(video_dest.resolve()),
        "srt_path": str(sub_dest.resolve()) if sub_dest else None,
        "quality": chosen_res
    }
