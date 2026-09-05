"""Export cookies for one or more domain suffixes from the CDP Chromium (127.0.0.1:9222) as Netscape cookies.txt.

Usage: python cdp_cookies.py <suffix[,suffix...]> <out-file>
Example: python cdp_cookies.py youtube.com,google.com /home/hermes/work/lore-engine/state/youtube_cookies.txt

The output file is created with mode 0600. Export YouTube cookies only for a throwaway account.
"""
import asyncio
import json
import os
import sys
import urllib.request

import websockets

suffixes = [s.strip().lstrip(".").lower() for s in sys.argv[1].split(",") if s.strip()]
out = sys.argv[2]
cdp = os.environ.get("LORE_CDP_URL", "http://127.0.0.1:9222")


def wanted(domain: str) -> bool:
    d = domain.lstrip(".").lower()
    return any(d == s or d.endswith("." + s) for s in suffixes)


async def main() -> None:
    ver = json.load(urllib.request.urlopen(f"{cdp}/json/version"))
    async with websockets.connect(ver["webSocketDebuggerUrl"], max_size=50 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                break
    cookies = [c for c in msg["result"]["cookies"] if wanted(c["domain"])]
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        dom = c["domain"]
        flag = "TRUE" if dom.startswith(".") else "FALSE"
        exp = int(c["expires"]) if c.get("expires", -1) > 0 else 0
        lines.append("\t".join([dom, flag, c["path"], "TRUE" if c["secure"] else "FALSE", str(exp), c["name"], c["value"]]))
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(out, 0o600)
    print(f"{len(cookies)} cookies for {suffixes} -> {out} (0600)")


asyncio.run(main())
