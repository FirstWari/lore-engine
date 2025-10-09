# ⚙️ The Lore Engine

**Every lecture has lore. Most of it is locked in 10-hour videos and cryptic PDFs.**

**The Lore Engine extracts it.**

## The Problem

You know the drill:

- **PDFs:** Your professor's 200-slide PDF, filled with nothing but bullet points, vague diagrams, and your own shattered hopes.
- **Handwritten notes:** That one dude's notes from 2018, scanned so badly they look like a seismograph reading of a metal concert. Good luck deciphering it 3 hours before finals.
- **Videos:** You're rewatching a 2-hour lecture for the fifth time trying to find *that one explanation*
- **Time sink:** "Let me just scrub through this 40-hour course real quick..." (Narrator: *It was not quick.*)
- **Comprehension gap:** Slides are too sparse, textbooks are too dense, videos are too slow. Handwriting too alien.

**What if you could transform all of it into comprehensive, readable notes?**

Lectures have the perfect amount of explanation—not a sparse slide deck, not a dense textbook. This tool gives you lecture-quality explanations for *everything*: your professor's cryptic PDFs, incomprehensible handwritten notes, and those endless video recordings.

## The Solution

The Lore Engine is a multimodal AI pipeline that transforms educational content—PDFs, videos, handwritten notes, and transcripts—into comprehensive, searchable markdown notes with explanations, screenshots and diagrams.

Think of it as a knowledge extraction engine: you feed it raw educational content, and it gives you organized, comprehensive "lore dumps."

**Before:** 10 hours of lecture watching  
**After:** 2 hours of focused reading (with full details and better explanations)

### See It In Action

<p align="center">
  <img src="assets/cli.gif" alt="Interactive CLI Demo" width="800">
  <br>
  <em>Interactive mode makes it dead simple to use</em>
</p>

## Features That Actually Matter

### Core Capabilities

- **📄 PDF → Detailed Notes**: Turn sparse slide decks into comprehensive explanations
- **✍️ Handwriting → Detailed Notes**: OCR and explain your professor's illegible scrawls  
- **📝 Transcripts + Video → Detailed Notes**: Take SRT files and add visual context + better formatting

### Intelligence

- **📸 Smart Screenshots**: Automatically captures key moments, not redundant frames
- **📊 Mermaid Diagrams**: Auto-generates flowcharts and architecture diagrams
- **🎯 Perceptual Deduplication**: Hash-based frame selection (no more 50 identical slides)
- **🤖 Context-Aware Explanations**: AI fills in the gaps between what's shown and what's implied

### Performance

- **🚀 Blazing Fast**: Process 10 hours of video in 40 minutes (15x real-time speed with 2 keys). Then consume in the next 4 hours.
- **⚡ Parallel Processing**: Multi-process pipeline + round-robin API keys = scales linearly
- **💾 Memory Efficient**: Doesn't load entire videos into RAM
- **🆓 Free-Tier Friendly**: Optimized for Gemini's generous free tier

**Performance:**

- Frame extraction: ~2-4 seconds per chunk (video_reader-rs, not OpenCV)
- Memory efficient: No whole-video allocation like Decord
- Scales linearly: 2 API keys = 30x real-time, 10 keys = 150x real-time
- CPU usage: ~3% (I/O bound, not compute bound)

## Real Examples

<p align="center">
  <img src="assets/output.gif" alt="Example Output" width="800">
  <br>
  <em>Clean, comprehensive markdown notes with screenshots and diagrams</em>
</p>

## Quick Start

### 1. Install Dependencies

**Recommended: Using uv (fastest)**

First, [install uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already.

```bash
git clone https://github.com/Slydite/lore-engine.git
cd lore-engine
uv sync
```

**Alternative: Using pip**

```bash
git clone https://github.com/Slydite/lore-engine.git
cd lore-engine
pip install -e .
```

**With dev dependencies:**

```bash
# Using uv
uv sync --all-extras

# Using pip
pip install -e ".[dev]"
```

> **Note:** This project uses `google-generativeai` (legacy SDK). We may migrate to the new `google-genai` SDK in the future. See [migration guide](https://ai.google.dev/gemini-api/docs/migrate#python) for differences.

**Note:** On Windows, you may need to install ffmpeg separately:

```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### 2. Get Your (Free) Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API Key"
3. Copy your key

### 3. Configure API Keys

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY_1=YOUR_GEMINI_API_KEY_HERE
```

**Pro tip:** Add multiple keys for faster parallel processing:

```bash
GEMINI_API_KEY_1=your_first_key_here
GEMINI_API_KEY_2=your_second_key_here
GEMINI_API_KEY_3=your_third_key_here
```

The engine uses numbered keys (`GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc.) in round-robin fashion. More keys = faster processing!

### 4. Run It

**Interactive Mode (easiest):**

```bash
# With uv (recommended)
uv run python src/main.py

# Or with regular Python (if using pip install)
cd src
python main.py
```

**Single File:**

```bash
# With uv
uv run python src/main.py --path "/path/to/lecture.mp4"

# Or with regular Python
python src/main.py --path "/path/to/lecture.mp4"
```

**Batch Process a Folder:**

```bash
# With uv
uv run python src/main.py --batch-path "/path/to/lectures/"

# Or with regular Python
python src/main.py --batch-path "/path/to/lectures/"
```

The tool will:

1. 📹 Extract smart keyframes from videos
2. 📝 Process transcripts (auto-detects `.srt` files)
3. 🤖 Generate comprehensive notes with Gemini
4. 💾 Save markdown files in the output directory

## How It Works (For The Nerds 🤓)

**1. Video or PDF Processing**

- Uses `video_reader-rs` (Rust FFmpeg bindings) instead of OpenCV for frame extraction
- Batch frame extraction via `get_batch()` API
- Memory efficient: only loads requested frames

**2. Intelligent Frame Selection for Videos**

- Perceptual hashing (pHash) with 8x8 DCT
- Temporal diversity scoring to avoid redundant frames
- Configurable similarity thresholds
- Global deduplication across entire video

**3. Multimodal AI Orchestration**

- Gemini 2.5 Flash for speed + quality balance (Any Gemini model works)
- Automatic fallback: inline images → File API for large batches
- Exponential backoff with intelligent retry logic
- Rate limiting to maximize free-tier throughput

**4. Output Processing**

- Automatic Mermaid diagram syntax correction
- Screenshot placeholder replacement with relative paths
- Markdown cleaning and formatting

### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Frame extraction | 2-4s per chunk | 1080p video, 5 frames |
| LLM inference | 10-20s per chunk | ~50 subtitles + images |
| Rate limiting | 10s between calls | Gemini free tier |
| Throughput | 15x real-time | With 2 API keys |
| Memory usage | <500MB | Excluding video file |

**Bottleneck:** LLM API calls (expected and unavoidable)  
**Not the bottleneck:** Frame extraction

## Configuration

Edit `config.json` to customize:

```json
{
  "model_name": "gemini-2.5-flash",
  "pages_per_chunk": 5,
  "lines_per_chunk": 50,
  "screenshots_per_minute": 3,
  "hash_similarity_threshold": 5,
  "request_interval": 10
}
```

**Key settings:**

- `screenshots_per_minute`: How many frames to extract per minute of video
- `hash_similarity_threshold`: Lower = more strict deduplication
- `request_interval`: Seconds between API calls (respect rate limits!)

## FAQ

**Q: Does this work with non-English content?**  
A: Yes! Gemini supports 100+ languages. Just make sure your SRT files are in the correct encoding (UTF-8). You will have to modify the base prompt to include your language.

**Q: Can I use this for copyrighted content?**  
A: The tool processes content locally and sends frames to Gemini's API. Follow your institution's fair use policies for educational content. Notes are derived content so should be fine :P but I am no legal expert.

**Q: Why Gemini and not GPT-5/Claude?**  
A: Gemini 2.5 has native multimodal support, generous free tier (60 RPM), and excellent performance on educational content. But the architecture is LLM-agnostic and model agnostic support coming soon!

**Q: How much does this cost?**  
A: **Free** if you stay within Gemini's limits. Heavy users might hit paid tiers.

**Q: Can I run this on my own LLM?**  
A: Not yet, but the architecture supports it. PRs welcome for OpenRouter(and alternatives) integration.

**Q: What about privacy?**  
A: The tool runs locally, however all content is sent to the Gemini API and Gemini Privacy Policy applies.

## Roadmap

- [ ] Local LLM/OpenRouter/Alternative support
- [ ] GUI interface
- [ ] Anki flashcard generation
- [ ] Custom prompt templates
- [ ] Better lecture support (whiteboard detection) - get latest fully annotated frame

## Contributing

Found a bug? Have a feature idea? PRs welcome!

**Areas where help is needed:**

- Testing on different video codecs
- Mermaid Diagram prompt
- LaTeX rendering improvements
- Local LLM integration
- UI/UX enhancements

*Star this repo if it extracted the lore from your professor's cryptic slides* ⭐
