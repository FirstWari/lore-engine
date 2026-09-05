"""Untrusted-text hygiene: filenames, transcript lines, log output.

Everything that comes from a remote page, a video title or a subtitle file is
third-party content. Before it becomes a path, a JSON field or a line on the
operator's terminal it goes through here.
"""

from __future__ import annotations

import re
import unicodedata

# C0/C1 controls (tab/newline kept), DEL, zero-width marks, bidi overrides/isolates, BOM
_CONTROL_RE = re.compile(
    "[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f-\\x9f"
    "\\u200b-\\u200f\\u202a-\\u202e\\u2066-\\u2069\\ufeff]"
)
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]")
_TAG_RE = re.compile(r"<[^>\n]{1,200}>")
_FS_BAD_RE = re.compile(r'[\\/*?:"<>|\x00-\x1f]')
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
MAX_NAME_LEN = 120


def clean_text(text: str, *, strip_tags: bool = False) -> str:
    """Remove control/bidi/zero-width characters (and optionally HTML tags); keep newlines and tabs."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text)
    t = _ANSI_RE.sub("", t)  # whole escape sequences first, then stray control bytes
    t = _CONTROL_RE.sub("", t)
    if strip_tags:
        t = _TAG_RE.sub("", t)
    return t


def sanitize_filename(name: str, fallback: str = "untitled") -> str:
    """Filesystem-safe single path component.

    Removes control/bidi characters and path separators, collapses whitespace,
    rejects ``.``/``..``/empty and Windows reserved device names, trims trailing
    dots/spaces and caps the length. Never returns something that can escape a
    directory.
    """
    t = clean_text(name or "")
    t = _FS_BAD_RE.sub("_", t)
    t = re.sub(r"\s+", " ", t).strip(" .")
    if not t or set(t) <= {".", "_", " "}:
        t = fallback
    if t.split(".")[0].upper() in _WINDOWS_RESERVED:
        t = "_" + t
    if len(t) > MAX_NAME_LEN:
        t = t[:MAX_NAME_LEN].rstrip(" .")
    return t or fallback


def safe_console(text: str, limit: int = 300) -> str:
    """Text that is safe to print to a terminal: no control sequences, bounded length."""
    t = clean_text(str(text)).replace("\n", " ").replace("\r", " ")
    return t if len(t) <= limit else t[: limit - 3] + "..."


def safe_id(value: str, fallback: str = "item", limit: int = 40) -> str:
    """Short identifier for directory suffixes (video id, lecture slug)."""
    t = re.sub(r"[^A-Za-z0-9_-]+", "-", clean_text(value or "")).strip("-")
    return t[:limit] or fallback
