# ⚙️ The Lore Engine

**Every lecture has lore. Most of it is locked in 10-hour videos and cryptic PDFs.**

**The Lore Engine extracts it.**

## The Problem

You know the drill:

- **PDFs:** Your professor's 200-slide deck has zero explanations. Just bullet points and diagrams. What do they even mean?
- **Handwritten notes:** That scan from 2018 looks like a seismograph during an earthquake. Good luck deciphering it.
- **Videos:** You're rewatching a 2-hour lecture for the fifth time trying to find *that one explanation*
- **Time sink:** "Let me just scrub through this 40-hour course real quick..." (Narrator: *It was not quick.*)
- **Comprehension gap:** Slides are too sparse, textbooks are too dense, videos are too slow
- You read at 500 WPM but watching at 4x speed still feels slow
- Videos are great for learning but *terrible* for reference

**What if you could transform all of it into comprehensive, readable notes?**

Lectures have the perfect amount of explanation—not a sparse slide deck, not a dense textbook. This tool gives you lecture-quality explanations for *everything*: your professor's cryptic PDFs, incomprehensible handwritten notes, and those endless video recordings.

## The Solution

The Lore Engine is a multimodal AI pipeline that transforms educational content—PDFs, videos, handwritten notes, and transcripts—into comprehensive, searchable markdown notes with explanations, screenshots, diagrams, and LaTeX math support.

Think of it as a knowledge extraction engine: you feed it raw educational content, and it gives you organized, comprehensive "lore dumps."

**Before:** 10 hours of lecture watching  
**After:** 2 hours of focused reading (with full details and better explanations)

<!-- GIF DEMO PLACEHOLDER -->
<p align="center">
  <img src="docs/demo.gif" alt="The Lore Engine Demo" width="800">
  <br>
  <em>Extracting the lore from hours of content</em>
</p>

## Features That Actually Matter

### Core Capabilities

- **📄 PDF → Detailed Notes**: Turn sparse slide decks into comprehensive explanations
- **✍️ Handwriting → Text**: OCR and explain your professor's illegible scrawls  
- **🎥 Video → Searchable Notes**: Extract, explain, and organize lecture content
- **📝 Transcripts → Enhanced Notes**: Take SRT files and add visual context + better formatting

### Intelligence

- **📸 Smart Screenshots**: Automatically captures key moments, not redundant frames
- **📊 Mermaid Diagrams**: Auto-generates flowcharts and architecture diagrams
- **🧮 LaTeX Math**: Proper equation formatting for STEM content
- **🎯 Perceptual Deduplication**: Hash-based frame selection (no more 50 identical slides)
- **🤖 Context-Aware Explanations**: AI fills in the gaps between what's shown and what's implied

### Performance

- **🚀 Blazing Fast**: Process 10 hours of video in 40 minutes (15x real-time speed)
- **⚡ Parallel Processing**: Multi-process pipeline + round-robin API keys = scales linearly
- **💾 Memory Efficient**: Doesn't load entire videos into RAM
- **🆓 Free-Tier Friendly**: Optimized for Gemini's generous free tier

**Performance:**

- Frame extraction: ~2-4 seconds per chunk (video_reader-rs, not OpenCV)
- Memory efficient: No whole-video allocation like Decord
- Scales linearly: 2 API keys = 30x real-time, 10 keys = 150x real-time
- CPU usage: ~3% (I/O bound, not compute bound)

## Real Examples

> **Note:** Example outputs coming soon! Processing lectures from MIT OCW, 3Blue1Brown, and system design channels.

### Use Cases

**📊 Sparse Slide Deck → Detailed Explanations**

- Input: Professor's 50-slide PDF with bullet points
- Output: Comprehensive notes explaining each concept, with diagrams and examples
- Time: 2 minutes to process, 15 minutes to read vs. 1 hour lecture

**🎥 Long Lecture → Searchable Reference**

- Input: 3-hour MIT OCW video on algorithms
- Output: Timestamped notes with screenshots, code examples, and complexity analysis
- Time: 18 minutes to process, 45 minutes to read vs. 3 hours watching

**✍️ Handwritten Notes → Clean Markdown**

- Input: Scanned pages of messy calculus derivations
- Output: LaTeX-formatted proofs with step-by-step explanations
- Time: 1 minute per page, instantly searchable

<!-- EXAMPLES SECTION - TO BE FILLED -->

<details>
<summary><b>📖 Example Output Structure (click to expand)</b></summary>

```markdown
# Distributed Systems - Part 1

## Consistent Hashing: An Introduction

### Overview
Consistent Hashing addresses the challenges of efficiently 
distributing data across a dynamic set of resources...

![Screenshot at 00:01:06](notes_screenshots/frame_00-01-06.jpg)

### The Problem with Simple Modulo Hashing

When using `h(R) % N`, adding a new server causes...

**Example calculations:**
- Request R1 (ID=10): `h(10) % 4 = 3` → Server S3
- Request R2 (ID=20): `h(20) % 4 = 3` → Server S3
- Request R3 (ID=35): `h(35) % 4 = 0` → Server S0

![Screenshot at 00:04:27](notes_screenshots/frame_00-04-27.jpg)

### Mathematical Analysis

The expected load per server is $\frac{X}{N}$ where:
- $X$ = total number of requests
- $N$ = number of servers

$$
\text{Load Factor} = \frac{1}{N}
$$

### System Architecture

```mermaid
graph TD
    Client[Client] -->|Request| LoadBalancer[Load Balancer]
    LoadBalancer -->|Hash: h(R) % N| Server1[Server 1]
    LoadBalancer --> Server2[Server 2]
    LoadBalancer --> Server3[Server 3]
```

```

</details>

## Quick Start

### 1. Install Dependencies

**Modern method with uv (fastest, recommended):**

```bash
git clone https://github.com/Slydite/lore-engine.git
cd lore-engine
uv sync
```

**Or with pip:**

```bash
pip install -e .
```

**With dev dependencies:**

```bash
# Using uv
uv sync --all-extras

# Using pip
pip install -e ".[dev]"
```

**Legacy method:**

```bash
pip install -r requirements.txt
```

**Note:** On Windows, you may need to install ffmpeg separately:

```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### 2. Get Your (Free) Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
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

**Alternative:** You can also set keys as environment variables or use a single comma-separated `GEMINI_API_KEY` variable.

### 4. Run It

**Interactive Mode (easiest):**

```bash
cd src
python main.py
```

**Single File:**

```bash
python main.py --path "/path/to/lecture.mp4"
```

**Batch Process a Folder:**

```bash
python main.py --batch-path "/path/to/lectures/"
```

The tool will:

1. 📹 Extract smart keyframes from videos
2. 📝 Process transcripts (auto-detects `.srt` files)
3. 🤖 Generate comprehensive notes with Gemini
4. 💾 Save markdown files in the output directory

## How It Works (For The Nerds 🤓)

### The Pipeline

```
Video Input → Frame Extraction → Perceptual Hashing → Diversity Selection
     ↓              ↓                    ↓                    ↓
  Transcript  →  Chunking  →  Multimodal AI  →  Markdown Notes
     ↓              ↓                    ↓                    ↓
Screenshots  ←  Timestamp Sync  ←  Diagram Gen  ←  LaTeX Math
```

### For the Nerds

**1. Video Processing (The Fast Part)**

- Uses `video_reader-rs` (Rust FFmpeg bindings) instead of OpenCV
- 10,000x faster than naive approaches
- Batch frame extraction via `get_batch()` API
- Memory efficient: only loads requested frames

**2. Intelligent Frame Selection**

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
- LaTeX math preservation
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
**Not the bottleneck:** Frame extraction (thanks, Rust!)

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
A: Yes! Gemini supports 100+ languages. Just make sure your SRT files are in the correct encoding (UTF-8). You will have to change a small line in the file src/prompt_library and replace english with your desired language.

**Q: Can I use this for copyrighted content?**  
A: The tool processes content locally and sends frames to Gemini's API. Follow your institution's fair use policies for educational content. Notes are derived content so should be fine :P

**Q: Why Gemini and not GPT-4/Claude?**  
A: Gemini 2.5 has native multimodal support, generous free tier (60 RPM), and excellent performance on educational content. But the architecture is LLM-agnostic and model agnostic support coming soon!

**Q: How much does this cost?**  
A: **Free** if you stay within Gemini's limits. Heavy users might hit paid tiers.

**Q: Can I run this on my own LLM?**  
A: Not yet, but the architecture supports it. PRs welcome for openrouter(and alternatives) integration.

**Q: What about privacy?**  
A: Your videos are processed locally. Only extracted frames and transcripts are sent to Gemini's API.

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

## License

MPL-2.0 License. Refer to LICENSE.MD for more details.

## Acknowledgments

Built with:

- [Google Gemini API](https://ai.google.dev/) - The AI brain
- [video_reader-rs](https://github.com/pythonlessons/video_reader-rs) - Rust-powered video decoding
- [imagehash](https://github.com/JohannesBuchner/imagehash) - Perceptual hashing
- [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) - Fast PDF rendering

---

**Made with ❤️ for students who need the lore, not the lecture**

*Star this repo if it extracted the lore from your professor's cryptic slides* ⭐
