---
name: lore-engine
description: Turn a lecture into material an AI can read and write notes from. Use when the user gives a lecture/course URL (Coursera, YouTube, any video site), a local video, or a slide PDF and wants notes, a summary, key moments, screenshots, or a study guide. One command, no API keys, runs locally.
version: 0.3.0
---

# lore-engine

One command turns a lecture into files you can read:

```bash
python lore.py <url | video.mp4 | slides.pdf>
```

It downloads the video and subtitles (URL), pulls the transcript, extracts
non-duplicate keyframes, and lays them out on 3x3 storyboard sheets. No LLM is
called. **You** (the agent running this) read the output and write the notes.

## Setup (once, per machine)

```bash
git clone https://github.com/Slydite/lore-engine.git
cd lore-engine
uv sync            # or: python -m venv .venv && source .venv/bin/activate && pip install -e .
```

Linux server (Debian/Ubuntu) one-liner for the optional system pieces:

```bash
sudo apt-get install -y ffmpeg fonts-dejavu-core   # ffmpeg: 720p+ merges; fonts: readable storyboard badges
curl -LsSf https://astral.sh/uv/install.sh | sh     # if uv is missing
```

Optional:

- `ffmpeg` on PATH: only needed to get 720p+ from YouTube-style sites (streams are merged). Without it you still get a single-file MP4, usually 360p.
- Fonts: the storyboard timestamp badge uses DejaVu / Liberation / Noto / Arial if present, else Pillow's bundled font, so a bare container still produces readable sheets.
- Memory: candidate frames are hashed in batches of 32 and only the winners are decoded again, so a two-hour 1080p lecture peaks at a few hundred MB. No tuning needed on small or large machines.
- **Coursera** needs your own logged-in cookies. In your browser install a "Get cookies.txt (Netscape format)" extension, open coursera.org while signed in, export, save as `www.coursera.org_cookies.txt` in the repo root (or set `COURSERA_COOKIE_FILE=/path/to/file` in `.env`). The file is a credential: it is git-ignored, never share it.
- `.env` (optional): `LORE_WORKSPACE_DIR=downloads` (where videos land), `COURSERA_COOKIE_FILE=...`.

## Run

Always run from the repo directory (or point Python at it):

```bash
python lore.py "https://www.coursera.org/learn/<course>/lecture/<id>/<slug>"
python lore.py "https://www.youtube.com/watch?v=..."
python lore.py ./lecture.mp4          # lecture.srt next to it is used if present
python lore.py ./slides.pdf
python lore.py <input> --out results --quality 720p --lang en --max-frames 27 --json
```

- `--out` results root (default `results/`), `--lang` subtitle language, `--max-frames` keyframes to keep (27 = 3 sheets), `--json` print only the final JSON line.
- On a server, run it detached and read the JSON afterwards: `nohup python lore.py "<url>" --json > run.json 2> run.log &` — `tail -1 run.json` is the index.
- Exit code 0 = success. On failure it prints one line `{"error": "..."}` and exits 1.
- The **last stdout line is always JSON** = the content of `index.json`. Parse that; do not scrape the progress lines (they go to stderr).

## What you get

```
results/<title>/
  index.json              everything below, with absolute paths + duration/word count
  transcript.txt          "[HH:MM:SS - HH:MM:SS] text" per subtitle (PDF: "[Page N]" blocks)
  transcript.srt          copy of the subtitle file (video only)
  keyframes/              frame_HH-MM-SS.jpg, visually distinct frames in time order (PDF: pages/)
  storyboard_page_01.jpg  3x3 sheets, each cell has its timestamp (or page) in the corner
```

Videos downloaded from URLs stay in `downloads/` (or `LORE_WORKSPACE_DIR`).

## How to work with the output (for the agent)

1. Read `index.json` first: it tells you the duration, whether a transcript exists (`transcript_txt`), and lists every image path. Check `warnings`.
2. For notes and summaries read `transcript.txt`. Every line carries a timestamp, so cite moments as `[MM:SS]`.
3. Only look at images when the words are not enough (diagrams, code on screen, formulas). Open `storyboard_page_NN.jpg` first: nine frames per image is cheap. If one frame matters, open the matching `keyframes/frame_HH-MM-SS.jpg` at full resolution.
4. If the user wants a specific moment, find the timestamp in `transcript.txt`, then pick the nearest keyframe by its filename.
5. Write the notes yourself (Markdown works well: headings per topic, timestamps, a short "key takeaways" list, embed keyframes with relative paths if the user wants visuals).

## Troubleshooting

| Symptom | Meaning / fix |
|---|---|
| `Coursera cookie file not found` | Export cookies as described in Setup, or pass `--cookies path`. |
| `Could not find window.App state` | Not enrolled in that course, wrong URL (must be a `/lecture/` page), or cookies expired: re-export. |
| `subtitle download failed` in `warnings` | The video is fine; the site rate-limited subtitles. Re-run later or use a local `.srt`. |
| `no subtitle file` warning | Local video without `.srt`. Transcribe first (e.g. whisper) and put `name.srt` next to `name.mp4`. |
| `video-reader-rs library is required` | Run `uv sync` inside the repo. |

## Installing this skill into an agent

Nothing to install for the tool itself beyond Setup. To make an agent *know* the command, give it this file:

- **Claude Code**: copy the repo folder (or just this `SKILL.md`) to `~/.claude/skills/lore-engine/SKILL.md`, or add one line to your project's `CLAUDE.md`: `For lectures/videos/PDFs run: python <path>/lore-engine/lore.py <input> (see that repo's SKILL.md).`
- **OpenAI Codex**: put the same folder under `~/.agents/skills/lore-engine/`, or reference it from `AGENTS.md`.
- **Gemini CLI**: add the "Run" and "How to work with the output" sections to your `GEMINI.md` (project or `~/.gemini/GEMINI.md`).
- **Hermes Agent**: copy the folder to `~/.hermes/skills/<category>/lore-engine/` (for example `~/.hermes/skills/research/lore-engine/`); it then shows up as `/lore-engine` and in the skill index. See https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- **Any other agent / chat model with shell access**: paste the "Run" and "How to work with the output" sections into its system prompt. The whole contract is one command and one folder.

Humans: same command in a terminal, then open `results/<title>/` and read.
