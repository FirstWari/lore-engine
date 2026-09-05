"""List lecture/reading item URLs of a Coursera course week page, through the logged-in browser.

Usage: python tools/coursera_links.py https://www.coursera.org/learn/<course>/home/week/1 [limit]
Prints one JSON line: {"lectures": [...], "readings": [...]}.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lore_engine import cdp_fetch  # noqa: E402

JS = """(() => {
  const abs = (h) => h.startsWith('http') ? h : 'https://www.coursera.org' + h;
  const uniq = (xs) => xs.filter((v, i, a) => a.indexOf(v) === i);
  const links = Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href') || '');
  return {
    lectures: uniq(links.filter(h => h.includes('/lecture/')).map(abs)),
    readings: uniq(links.filter(h => h.includes('/supplement/')).map(abs)),
  };
})()"""


def main() -> int:
    url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    tid, tab = cdp_fetch.open_page(url, timeout=60)
    try:
        data = tab.evaluate(JS) or {"lectures": [], "readings": []}
    finally:
        tab.close()
        cdp_fetch.close_target(tid)
    print(json.dumps({k: v[:limit] for k, v in data.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
