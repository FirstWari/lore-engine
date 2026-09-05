"""Small, dependency-free HTML -> Markdown for Coursera reading pages.

Handles headings, paragraphs, lists, code/pre, links, images, emphasis, tables
(flattened row by row) and drops scripts/styles/nav. Output is passed through
``textsafe.clean_text`` by the caller.
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_BLOCK = {"p", "div", "section", "article", "li", "ul", "ol", "table", "tr", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}
_SKIP = {"script", "style", "noscript", "svg", "nav", "button", "iframe", "template"}


class _MD(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.list_stack: list[tuple[str, int]] = []
        self.in_pre = False
        self.in_code = False
        self.href: str | None = None
        self.cell_sep = False

    def _nl(self, n: int = 1) -> None:
        text = "".join(self.out)
        trailing = len(text) - len(text.rstrip("\n"))
        if trailing < n:
            self.out.append("\n" * (n - trailing))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in _SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._nl(2)
            self.out.append("#" * int(tag[1]) + " ")
        elif tag == "p" or tag == "div" or tag == "section" or tag == "article" or tag == "blockquote":
            self._nl(2 if tag != "div" else 1)
            if tag == "blockquote":
                self.out.append("> ")
        elif tag in ("ul", "ol"):
            self._nl(1)
            self.list_stack.append((tag, 0))
        elif tag == "li":
            self._nl(1)
            kind, n = self.list_stack[-1] if self.list_stack else ("ul", 0)
            indent = "  " * (len(self.list_stack) - 1)
            if kind == "ol":
                n += 1
                self.list_stack[-1] = (kind, n)
                self.out.append(f"{indent}{n}. ")
            else:
                self.out.append(f"{indent}- ")
        elif tag == "pre":
            self._nl(2)
            self.out.append("```\n")
            self.in_pre = True
        elif tag == "code" and not self.in_pre:
            self.out.append("`")
            self.in_code = True
        elif tag in ("strong", "b"):
            self.out.append("**")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag == "a":
            self.href = a.get("href")
            self.out.append("[")
        elif tag == "img":
            alt = (a.get("alt") or "image").strip()
            src = a.get("src") or ""
            self.out.append(f"![{alt}]({src})")
        elif tag == "br":
            self.out.append("\n")
        elif tag == "hr":
            self._nl(2)
            self.out.append("---\n\n")
        elif tag == "tr":
            self._nl(1)
            self.out.append("| ")
            self.cell_sep = False
        elif tag in ("td", "th"):
            if self.cell_sep:
                self.out.append(" | ")
            self.cell_sep = True
        elif tag == "table":
            self._nl(2)

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "table"):
            self._nl(2)
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            self._nl(1)
        elif tag == "li" or tag == "div" or tag == "section" or tag == "article":
            self._nl(1)
        elif tag == "pre":
            self._nl(1)
            self.out.append("```\n\n")
            self.in_pre = False
        elif tag == "code" and self.in_code:
            self.out.append("`")
            self.in_code = False
        elif tag in ("strong", "b"):
            self.out.append("**")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag == "a":
            href = self.href or ""
            self.out.append(f"]({href})" if href else "]")
            self.href = None
        elif tag == "tr":
            self.out.append(" |\n")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.in_pre:
            self.out.append(data)
        else:
            self.out.append(re.sub(r"[ \t\r\n]+", " ", data))


def html_to_markdown(html: str) -> str:
    p = _MD()
    p.feed(unescape(html) if "&lt;" in html and "<" not in html else html)
    p.close()
    text = "".join(p.out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
