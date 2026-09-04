"""PDF document extraction module (text + high-res slide images) for lore-engine."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdfium2 as pdfium

def get_pdf_info(pdf_path: str | Path) -> Dict[str, Any]:
    """Get metadata and page count for a PDF file."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    pdf = pdfium.PdfDocument(str(path))
    total_pages = len(pdf)
    
    first_page = pdf[0] if total_pages > 0 else None
    width, height = (first_page.get_size()) if first_page else (0, 0)
    
    metadata = {}
    try:
        metadata = {
            "title": pdf.get_metadata_dict().get("Title", ""),
            "author": pdf.get_metadata_dict().get("Author", ""),
            "creator": pdf.get_metadata_dict().get("Creator", ""),
        }
    except Exception:
        pass
        
    pdf.close()
    return {
        "pdf_path": str(path.resolve()),
        "total_pages": total_pages,
        "first_page_width": round(width, 1),
        "first_page_height": round(height, 1),
        "metadata": metadata
    }

def extract_pdf_content(
    pdf_path: str | Path,
    start_page: int = 1,
    end_page: Optional[int] = None,
    output_dir: Optional[str | Path] = None,
    extract_text: bool = True,
    render_images: bool = True,
    render_scale: float = 2.0
) -> List[Dict[str, Any]]:
    """
    Extract text and/or slide images from a PDF page range.
    Page numbers are 1-indexed.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    pdf = pdfium.PdfDocument(str(path))
    total_pages = len(pdf)

    if end_page is None or end_page > total_pages:
        end_page = total_pages

    start_idx = max(0, start_page - 1)
    end_idx = min(total_pages, end_page)

    if output_dir is None and render_images:
        stem = path.stem
        output_dir = Path("results") / stem / "slides"
    elif output_dir:
        output_dir = Path(output_dir)
        
    if output_dir and render_images:
        output_dir.mkdir(parents=True, exist_ok=True)

    extracted_pages = []

    for idx in range(start_idx, end_idx):
        page_num = idx + 1
        page = pdf[idx]
        
        page_text = ""
        if extract_text:
            textpage = page.get_textpage()
            page_text = textpage.get_text_range()

        image_path = None
        if render_images and output_dir:
            bitmap = page.render(scale=render_scale)
            pil_img = bitmap.to_pil().convert("RGB")
            out_file = output_dir / f"page_{page_num:03d}.jpg"
            pil_img.save(str(out_file), "JPEG", quality=85)
            image_path = str(out_file.resolve())

        page.close()

        extracted_pages.append({
            "page_number": page_num,
            "text": page_text.strip(),
            "char_count": len(page_text.strip()),
            "image_path": image_path
        })

    pdf.close()
    return extracted_pages
