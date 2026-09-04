"""Storyboard grid generator for visual lecture summaries."""

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PADDING = 16
BG_COLOR = (24, 24, 27)  # Dark modern slate
BORDER_COLOR = (63, 63, 70)  # Frame border
TS_TEXT_COLOR = (250, 204, 21)  # Yellow timestamp text


#: Font *names* first (Pillow searches the OS font directories: /usr/share/fonts,
#: ~/.fonts, /Library/Fonts, C:/Windows/Fonts), then explicit Linux/macOS/Windows paths.
FONT_CANDIDATES = (
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "NotoSans-Regular.ttf",
    "Arial.ttf",
    "arial.ttf",
    "Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
)


def get_font(size: int = 18) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Return a readable font at ``size`` on Linux, macOS or Windows.

    Falls back to Pillow's bundled scalable font, so timestamp badges stay
    legible on a bare server with no system fonts installed.
    """
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no size argument
        return ImageFont.load_default()


def compile_storyboard_sheets(
    frames: list[dict[str, Any]],  # List of {"timestamp": str, "image_path": str}
    output_dir: str | Path,
    title: str = "Lecture Storyboard",
    prefix: str = "storyboard",
    cell_w: int = 640,
    cell_h: int = 360,
    jpeg_quality: int = 88,
) -> list[dict[str, Any]]:
    """
    Compile a sequence of timestamped keyframe images into 3x3 storyboard sheets.
    Returns list of compiled sheet info.
    """
    if not frames:
        return []

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    pages = [frames[i : i + 9] for i in range(0, len(frames), 9)]
    created_sheets = []
    font = get_font(18)

    for page_idx, page_frames in enumerate(pages):
        cols = 3 if len(page_frames) >= 3 else len(page_frames)
        rows = math.ceil(len(page_frames) / 3)

        canvas_w = cols * cell_w + (cols + 1) * PADDING
        canvas_h = rows * cell_h + (rows + 1) * PADDING

        canvas = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
        draw = ImageDraw.Draw(canvas)

        for idx, frame_info in enumerate(page_frames):
            col = idx % 3
            row = idx // 3
            x = PADDING + col * (cell_w + PADDING)
            y = PADDING + row * (cell_h + PADDING)

            img_file = frame_info["image_path"]
            ts_label = frame_info["timestamp"]

            try:
                with Image.open(img_file) as img:
                    img_rgb = img.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
                    canvas.paste(img_rgb, (x, y))
            except Exception:
                continue

            # Frame border
            draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=BORDER_COLOR, width=2)

            # Timestamp badge
            badge_text = f" {ts_label} "
            try:
                text_w = int(draw.textlength(badge_text, font=font))
            except Exception:
                text_w = len(badge_text) * 10
            text_h = 24

            draw.rectangle([x + 6, y + 6, x + 6 + text_w, y + 6 + text_h], fill=(0, 0, 0))
            draw.text((x + 6, y + 6), badge_text, fill=TS_TEXT_COLOR, font=font)

        sheet_filename = f"{prefix}_page_{page_idx + 1:02d}.jpg"
        sheet_path = out_path / sheet_filename
        canvas.save(str(sheet_path), "JPEG", quality=jpeg_quality)

        created_sheets.append(
            {
                "page": page_idx + 1,
                "total_pages": len(pages),
                "frame_count": len(page_frames),
                "image_path": str(sheet_path.resolve()),
                "start_time": page_frames[0]["timestamp"],
                "end_time": page_frames[-1]["timestamp"],
            }
        )

    return created_sheets
