"""Fetch Coursera pages through the *real* logged-in Chromium (CDP), not from Python.

Why: the browser owns the session (cookies, UA, TLS, JS). Requests made from it
are indistinguishable from the user opening the page. Python only ever touches
the CDN media URL afterwards.

How: HTTP ``PUT /json/new?<url>`` opens a tab with no automation client attached
while the page loads; then a short WebSocket session evaluates JavaScript in an
*isolated world* (no ``Runtime.enable``, no ``Console.enable``) to read
``window.App`` and to ``fetch()`` subtitle/asset text with the browser's own
credentials; finally the tab is closed.

Only ``websockets`` is needed (``pip install lore-engine[browser]``).
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any


class CdpError(RuntimeError):
    code = "CDP_UNREACHABLE"


class CourseraSessionError(RuntimeError):
    code = "COURSERA_SESSION"


class CourseraPageError(RuntimeError):
    code = "COURSERA_PAGE_FORMAT"


def cdp_url() -> str:
    return os.environ.get("LORE_CDP_URL", "http://127.0.0.1:9222").rstrip("/")


# The CDP endpoint is local: never send it through HTTP(S)_PROXY (WARP is for the browser, not for us).
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http_json(url: str, method: str = "GET", timeout: float = 10.0) -> Any:
    req = urllib.request.Request(url, method=method)
    with _LOCAL_OPENER.open(req, timeout=timeout) as resp:  # local CDP endpoint only
        return json.loads(resp.read().decode("utf-8"))


class _Tab:
    """One CDP page session with an isolated world. Sync API on top of websockets."""

    def __init__(self, ws_url: str, timeout: float):
        try:
            from websockets.sync.client import connect  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise CdpError("websockets is required: pip install 'lore-engine[browser]'") from exc
        try:
            self.ws = connect(ws_url, max_size=64 * 1024 * 1024, open_timeout=timeout, proxy=None)
        except TypeError:  # older websockets without the proxy parameter
            self.ws = connect(ws_url, max_size=64 * 1024 * 1024, open_timeout=timeout)
        self.timeout = timeout
        self._id = 0
        self._ctx: int | None = None
        self.frame_id: str | None = None

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:  # noqa: BLE001
            pass

    def send(self, method: str, **params: Any) -> dict[str, Any]:
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            raw = self.ws.recv(timeout=max(0.1, deadline - time.time()))
            msg = json.loads(raw)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise CdpError(f"{method}: {msg['error'].get('message')}")
                return msg.get("result", {})
        raise CdpError(f"{method}: timeout")

    def isolated_context(self, frame_id: str) -> int:
        if self._ctx is None:
            res = self.send("Page.createIsolatedWorld", frameId=frame_id, worldName="lore", grantUniveralAccess=False)
            self._ctx = int(res["executionContextId"])
        return self._ctx

    def evaluate(self, expression: str, *, await_promise: bool = False, main_world: bool = False) -> Any:
        """Evaluate JS. Default: the isolated world (DOM access, fetch with credentials, invisible to page
        scripts). ``main_world=True`` reads page globals such as ``window.App`` — a plain Runtime.evaluate,
        no Runtime.enable/Console.enable, so no CDP subscription is ever created."""
        params: dict[str, Any] = {"expression": expression, "returnByValue": True, "awaitPromise": await_promise}
        if self._ctx is not None and not main_world:
            params["contextId"] = self._ctx
        try:
            res = self.send("Runtime.evaluate", **params)
        except CdpError as exc:
            if "Cannot find context" in str(exc) and self.frame_id and not main_world:
                # the document was replaced (SPA redirect); rebuild the isolated world once
                self._ctx = None
                self.frame_id = self.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
                params["contextId"] = self.isolated_context(self.frame_id)
                res = self.send("Runtime.evaluate", **params)
            else:
                raise
        if "exceptionDetails" in res:
            raise CdpError(f"evaluate failed: {res['exceptionDetails'].get('text')}")
        return res.get("result", {}).get("value")


def open_page(url: str, *, settle_sec: float = 3.0, timeout: float = 60.0) -> tuple[str, _Tab]:
    """Open ``url`` in a new tab, wait for load, return (targetId, tab) with an isolated world ready."""
    base = cdp_url()
    try:
        info = _http_json(f"{base}/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
    except Exception as exc:  # noqa: BLE001
        raise CdpError(f"cannot open tab via {base}: {exc}") from exc
    target_id = info["id"]
    tab = _Tab(info["webSocketDebuggerUrl"], timeout)
    try:
        # frame id for the isolated world; Page.getFrameTree needs no Page.enable
        frame_id = tab.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
        deadline = time.time() + timeout
        last_url, stable = None, 0
        while time.time() < deadline:
            state = tab.send("Runtime.evaluate", expression="document.readyState + ' ' + location.href", returnByValue=True)
            value = state.get("result", {}).get("value") or ""
            ready, _, cur_url = value.partition(" ")
            if ready == "complete" and cur_url == last_url:
                stable += 1
                if stable >= 2:  # same URL for two polls: SPA redirects have settled
                    break
            else:
                stable = 0
            last_url = cur_url
            time.sleep(0.5)
        time.sleep(settle_sec)
        tab.frame_id = tab.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
        tab.isolated_context(tab.frame_id)
        return target_id, tab
    except Exception:
        tab.close()
        close_target(target_id)
        raise


def close_target(target_id: str) -> None:
    try:
        _LOCAL_OPENER.open(f"{cdp_url()}/json/close/{target_id}", timeout=5).read()
    except Exception:  # noqa: BLE001
        pass


_APP_STORES_JS = """(() => {
  const app = window.App;
  if (!app) return null;
  const stores = (((app.context || {}).dispatcher || {}).stores) || {};
  return stores;
})()"""


def _is_login_page(tab: _Tab) -> bool:
    return bool(tab.evaluate(
        "(() => { const u = location.href; return /\\/login|\\/signup|accounts\\.google\\.com/.test(u) "
        "|| !!document.querySelector('form[action*=\"login\"], input[type=\"password\"]'); })()"
    ))


def pick_language(preferred: str | None, available: list[str], hints: list[str]) -> str | None:
    """Choose a subtitle language: explicit preference (if available) > course language hint > en > first."""
    if not available:
        return None
    avail = {a.lower(): a for a in available}

    def match(code: str | None) -> str | None:
        if not code:
            return None
        c = code.lower()
        if c in avail:
            return avail[c]
        base = c.split("-")[0]
        for k, v in avail.items():
            if k.split("-")[0] == base:
                return v
        return None

    if preferred and preferred.lower() != "auto":
        found = match(preferred)
        if found:
            return found
    for h in hints:
        found = match(h)
        if found:
            return found
    return match("en") or available[0]


def fetch_coursera_page(url: str, *, sub_lang: str | None = "auto", timeout: float = 60.0) -> dict[str, Any]:
    """Open a Coursera item page in the real browser and return what lore needs.

    Result keys: ``kind`` ("lecture" | "reading" | "other"), ``title``, ``url``,
    ``video`` (videoData dict for lectures), ``subtitle_text`` (fetched in-browser,
    original language preferred), ``subtitle_lang``, ``languages`` (available),
    ``reading_html`` (main content HTML for readings), ``assets`` (list of
    {name,url} for downloadable files found in the page state).
    """
    target_id, tab = open_page(url, timeout=timeout)
    try:
        if _is_login_page(tab):
            raise CourseraSessionError("Coursera session is not logged in (login page shown); log in via noVNC")
        has_app = tab.evaluate("!!window.App", main_world=True)
        if not has_app:
            # SPA may still be hydrating
            for _ in range(10):
                time.sleep(1.0)
                if tab.evaluate("!!window.App", main_world=True):
                    has_app = True
                    break
        if not has_app:
            raise CourseraPageError("window.App not found on the page (not a course item page, or page format changed)")
        # The item body renders after hydration: wait for the CML viewer / video / lab frame (max ~25 s).
        ready_js = ("!!document.querySelector('[data-testid=\"cml-viewer\"], .rc-CML, video, "
                    "[data-testid=\"course-frame-content\"], iframe[src^=\"http\"]')")
        for _ in range(25):
            if tab.evaluate(ready_js):
                break
            time.sleep(1.0)
        time.sleep(1.0)

        data = tab.evaluate("""(() => {
          const stores = (((window.App.context || {}).dispatcher || {}).stores) || {};
          const vs = stores.VideoItemStore || {};
          const vd = vs.videoData || null;
          const h1 = document.querySelector('h1');
          const out = {title: (h1 && h1.innerText.trim()) || document.title, url: location.href, video: vd, storeNames: Object.keys(stores)};
          // course/primary language hints (best effort, schema varies)
          const cand = [];
          const walk = (o, depth) => {
            if (!o || typeof o !== 'object' || depth > 4) return;
            for (const k of Object.keys(o)) {
              const v = o[k];
              if (/^(primaryLanguageCode|primaryLanguage|courseLanguage|languageCode)$/.test(k) && typeof v === 'string') cand.push(v);
              else if (typeof v === 'object') walk(v, depth + 1);
            }
          };
          for (const name of Object.keys(stores)) { try { walk(stores[name], 0); } catch (e) {} }
          out.langHints = cand.slice(0, 8);
          // readings: main content
          const main = document.querySelector('[data-testid="cds-content"], .rc-CML, [role="main"], main');
          out.readingHtml = main ? main.innerHTML.slice(0, 3_000_000) : null;
          // external tools (ungraded labs): iframe targets and launch links, appended as a source list
          const ext = [];
          for (const f of document.querySelectorAll('iframe[src]')) if (/^https?:/.test(f.src)) ext.push(f.src);
          for (const a of document.querySelectorAll('a[href]')) if (/launch|open tool|start lab|labs\.|skills\.network/i.test((a.textContent||'') + ' ' + a.href)) ext.push(a.href);
          out.externalLinks = ext.filter((v,i,a)=>a.indexOf(v)===i).slice(0, 10);
          // downloadable assets referenced in page state or DOM (pdf/pptx/zip/ipynb/docx)
          const assets = [];
          for (const a of document.querySelectorAll('a[href]')) {
            const h = a.href || '';
            if (/\\.(pdf|pptx?|zip|ipynb|docx?|xlsx?|csv|txt|py|R)(\\?|$)/i.test(h) || /\\/api\\/rest\\/v1\\/asset\\//.test(h)) {
              assets.push({name: (a.textContent || '').trim().slice(0, 120) || h.split('/').pop().split('?')[0], url: h});
            }
          }
          out.assets = assets.slice(0, 50);
          return out;
        })()""", main_world=True)
        if not data:
            raise CourseraPageError("could not read page state")
        kind = "lecture" if data.get("video") and (data["video"].get("sources") or {}).get("byResolution") else (
            "reading" if data.get("readingHtml") else "other")
        result: dict[str, Any] = {
            "kind": kind, "title": data.get("title") or "", "url": data.get("url") or url,
            "video": data.get("video"), "lang_hints": data.get("langHints") or [],
            "reading_html": data.get("readingHtml") if kind == "reading" else None,
            "external_links": data.get("externalLinks") or [],
            "assets": data.get("assets") or [], "store_names": data.get("storeNames") or [],
            "subtitle_text": None, "subtitle_lang": None, "languages": [],
        }
        if kind == "lecture":
            subs = (data["video"].get("subtitles") or {})
            result["languages"] = sorted(subs.keys())
            lang = pick_language(sub_lang, result["languages"], result["lang_hints"])
            part = subs.get(lang) if lang else None
            if part:
                sub_url = part if part.startswith("http") else "https://www.coursera.org" + (part if part.startswith("/") else "/" + part)
                if urllib.parse.urlparse(sub_url).hostname and urllib.parse.urlparse(sub_url).hostname.endswith("coursera.org"):
                    js = (
                        "fetch(" + json.dumps(sub_url) + ", {credentials: 'include'})"
                        ".then(r => r.ok ? r.text() : Promise.reject(new Error('HTTP ' + r.status)))"
                    )
                    try:
                        text = tab.evaluate(js, await_promise=True)
                        if isinstance(text, str) and text.strip():
                            result["subtitle_text"], result["subtitle_lang"] = text, lang
                    except CdpError as exc:
                        result["subtitle_error"] = str(exc)
        return result
    finally:
        tab.close()
        close_target(target_id)


def fetch_text_in_browser(page_url: str, resource_url: str, *, timeout: float = 60.0) -> str:
    """Fetch a same-site resource (subtitle .vtt/.srt) from inside a browser tab on ``page_url``.

    The request carries the browser's cookies/UA/TLS; Python never sees the session.
    """
    host = (urllib.parse.urlparse(resource_url).hostname or "").lower()
    if not host.endswith("coursera.org"):
        raise CourseraPageError(f"refusing in-browser fetch of non-Coursera host: {host}")
    target_id, tab = open_page(page_url, settle_sec=1.0, timeout=timeout)
    try:
        js = (
            "fetch(" + json.dumps(resource_url) + ", {credentials: 'include'})"
            ".then(r => r.ok ? r.text() : Promise.reject(new Error('HTTP ' + r.status)))"
        )
        text = tab.evaluate(js, await_promise=True)
        if not isinstance(text, str):
            raise CourseraPageError("subtitle fetch returned no text")
        return text
    finally:
        tab.close()
        close_target(target_id)
