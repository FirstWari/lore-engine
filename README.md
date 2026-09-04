# The Lore Engine

**Every lecture has lore. Most of it is locked in 10-hour videos and cryptic PDFs.**

Lore Engine is one command that turns a lecture into files an AI agent (or you) can read:

```bash
python lore.py "https://www.coursera.org/learn/<course>/lecture/<id>/<slug>"   # needs your exported cookies
python lore.py "https://www.youtube.com/watch?v=..."                            # any yt-dlp site
python lore.py ./lecture.mp4                                                    # .srt beside it is used
python lore.py ./slides.pdf
```

```
results/<title>/
  index.json              everything below with absolute paths (also the last stdout line, as JSON)
  transcript.txt          "[HH:MM:SS - HH:MM:SS] text" per subtitle (PDF: "[Page N]" blocks)
  transcript.srt          copy of the subtitles (video only)
  keyframes/              visually distinct frames, frame_HH-MM-SS.jpg (PDF: pages/)
  storyboard_page_NN.jpg  3x3 contact sheets, each cell stamped with its timestamp
```

No LLM is called and no API key is needed. The agent you already use (Claude Code, Codex,
Gemini CLI, Hermes, ...) reads `transcript.txt` for the words and the storyboard sheets for
the visuals, then writes the notes. **[SKILL.md](SKILL.md)** is the full contract: setup,
Coursera cookies, how an agent should read the output, troubleshooting, and how to register
the skill in each agent.

## Install

```bash
git clone https://github.com/Slydite/lore-engine.git
cd lore-engine
uv sync            # or: python -m venv .venv && .venv/Scripts/activate && pip install -e .
```

Optional: `ffmpeg` on PATH for 720p+ downloads from YouTube-style sites (streams get merged;
without it you still get a single-file MP4). Coursera needs a Netscape `cookies.txt` export of
your logged-in browser, saved as `www.coursera.org_cookies.txt` in the repo root or pointed to
by `COURSERA_COOKIE_FILE` in `.env`. It is a credential: git-ignored, never share it.

## How it works

| Step | What happens |
|---|---|
| Download | Coursera pages are read with your cookies (the page state carries the MP4 + subtitle URLs); everything else goes through `yt-dlp` with one best-effort subtitle track. |
| Transcript | The `.srt` is rendered to timestamped plain text plus duration / word-count stats. |
| Keyframes | Frames are sampled every ~10 s with `video-reader-rs` (Rust decoder, no whole-video RAM), fingerprinted with a perceptual hash, and picked for diversity. Thresholds relax automatically so screen recordings (notebooks, terminals) still yield enough frames. |
| Storyboard | Nine frames per sheet with timestamp badges: cheap for a multimodal model to scan, and each cell maps back to a full-resolution file in `keyframes/`. |
| PDF | Pages are rendered at 2x with `pypdfium2`; text per page goes to `transcript.txt`. |

Layout:

```
lore.py            the command
lore_engine/       downloader.py  transcripts.py  video.py  storyboard.py  pdf.py
tests/             pytest, no network or video decoding needed
SKILL.md           the agent-facing contract
```

## Options

`--out results` results root · `--quality 720p` · `--lang en` subtitle language · `--cookies path` ·
`--max-frames 27` keyframes to keep (27 = 3 sheets) · `--json` print only the final JSON line.
Exit code 0 on success; on failure one `{"error": "..."}` line and exit 1.

## Contributing

`uv sync --extra dev`, then `pytest` and `ruff check .`. PRs welcome: more sites, whiteboard
detection (keep the latest fully annotated frame), OCR of frames.

MIT License.
