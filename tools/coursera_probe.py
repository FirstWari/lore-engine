"""Diagnostic: show how a Coursera item page is structured (containers, titles, video keys).

Usage: python tools/coursera_probe.py <url>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lore_engine import cdp_fetch  # noqa: E402

DOM_JS = """(() => {
  const out = {url: location.href, title: document.title};
  out.h1 = Array.from(document.querySelectorAll('h1')).map(h => h.innerText.trim()).slice(0, 3);
  out.h2 = Array.from(document.querySelectorAll('h2')).map(h => h.innerText.trim()).slice(0, 5);
  const cands = [];
  for (const el of document.querySelectorAll('main, [role="main"], article, [data-testid], [class*="rc-"], [class*="cml"], [class*="Cml"], [class*="reading"], [class*="Reading"], [class*="supplement"]')) {
    const t = (el.innerText || '').trim();
    if (t.length > 400) cands.push({tag: el.tagName, id: el.id, cls: String(el.className).slice(0, 80), testid: el.getAttribute('data-testid'), len: t.length, sample: t.slice(0, 80)});
  }
  cands.sort((a, b) => a.len - b.len);
  out.containers = cands.slice(0, 12);
  out.iframes = Array.from(document.querySelectorAll('iframe[src]')).map(f => f.src).slice(0, 5);
  return out;
})()"""

APP_JS = """(() => {
  const stores = (((window.App || {}).context || {}).dispatcher || {}).stores || {};
  const vd = (stores.VideoItemStore || {}).videoData || null;
  return {storeNames: Object.keys(stores).slice(0, 40), videoKeys: vd ? Object.keys(vd) : null,
          videoName: vd ? (vd.name || vd.title || null) : null};
})()"""


def main() -> int:
    url = sys.argv[1]
    tid, tab = cdp_fetch.open_page(url, timeout=60)
    try:
        dom = tab.evaluate(DOM_JS)
        app = tab.evaluate(APP_JS, main_world=True)
    finally:
        tab.close()
        cdp_fetch.close_target(tid)
    print(json.dumps({"dom": dom, "app": app}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
