import os
import logging
import sys
from typing import Dict, Any

# sys.path manipulation removed - use proper Python package imports

from notes_generator.processors.base_processor import BaseNotesProcessor

logger = logging.getLogger(__name__)


class PDFNotesProcessor(BaseNotesProcessor):
    """
    Processor for PDF files.
    
    Extracts images from PDF pages and generates markdown notes using LLM.
    Supports optional inclusion of page images in the output.
    """
    
    def process(self, file_path: str, output_dir: str, prompt_type: str = None, 
                custom_prompt: str = None, conciseness: str = None, output_format: str = None,
                tools: list = None, start_page: int = 0, **kwargs) -> None:
        """
        Process a PDF file and generate markdown notes.
        
        Args:
            file_path: Path to the PDF file
            output_dir: Directory for output files
            prompt_type: Type of prompt to use (defaults to config value)
            custom_prompt: Custom prompt text
            conciseness: Conciseness level ('short_hand', 'balanced', 'deep_dive')
            start_page: Page number to start processing from (0-indexed)
            **kwargs: Additional arguments (ignored)
        """
        if prompt_type is None:
            prompt_type = self.config.get("prompt_type")

        def pdf_chunk_processor(source_path: str, user_prompt: str, paths: Dict[str, str]):
            """Generator that yields PDF chunks for processing."""
            pages_per_chunk = self.config.get("pages_per_chunk")
            current_page = start_page

            while True:
                image_chunk = self.content_extractor.extract_images_from_pdf(
                    source_path, current_page, pages_per_chunk
                )
                if not image_chunk:
                    logger.info("No more pages to process")
                    break

                chunk_info = f"pages {current_page + 1}-{current_page + len(image_chunk)}"
                
                # Create chunk data with images and processing info
                chunk_data = {
                    'images': image_chunk,
                    'current_page': current_page,
                    'paths': paths
                }
                
                yield chunk_data, chunk_info
                current_page += len(image_chunk)

        self._process_source(file_path, output_dir, prompt_type, custom_prompt, pdf_chunk_processor, 
                            conciseness, output_format, tools)

    def _process_single_chunk(self, chunk_data: Dict[str, Any], user_prompt: str, paths: Dict[str, str]) -> str:
        """
        Process a single PDF chunk with images.
        
        Args:
            chunk_data: Dictionary containing 'images', 'current_page', and 'paths'
            user_prompt: The prompt to use for LLM interaction
            paths: Dictionary containing output path information
            
        Returns:
            str: Processed markdown content with optional image links
        """
        image_chunk = chunk_data['images']
        current_page = chunk_data['current_page']
        num_pages_in_chunk = len(image_chunk)
        
        # Build image inventory for this chunk
        page_references = []
        for i in range(num_pages_in_chunk):
            page_num_in_doc = current_page + i + 1
            page_references.append(f"- [PAGE-{page_num_in_doc}]: Page/Slide {page_num_in_doc}")
        
        available_pages_text = "\n".join(page_references)
        
        # Inject image inventory into the prompt
        full_prompt = (
            f"{user_prompt}\n\n"
            f"---\n\n"
            f"**AVAILABLE IMAGES FOR THIS CHUNK:**\n"
            f"{available_pages_text}\n\n"
            f"Use [PAGE-N] tags to reference and inline specific pages at appropriate locations in your notes.\n"
            f"Example: [PAGE-1] will display the first page/slide image."
        )
        
        # Generate markdown from images with enhanced prompt
        markdown_output, self.llm_interaction.last_request_time = self.llm_interaction.generate_markdown_notes(
            image_chunk, full_prompt
        )
        cleaned_markdown = self.markdown_utils.clean_markdown(markdown_output)
        # Create a dedicated directory for this PDF's screenshots
        base_screenshot_dir = os.path.join(paths['output_dir'], "notes_screenshots")
        pdf_screenshot_dir = os.path.join(
            base_screenshot_dir, 
            f"{paths['fs_safe_prefix']}_{paths['fs_safe_name']}_screenshots"
        )
        os.makedirs(pdf_screenshot_dir, exist_ok=True)
        
        # Save images and build mapping for placeholder replacement
        saved_pages_map = {}
        for i, img in enumerate(image_chunk):
            page_num_in_doc = current_page + i + 1
            img_path = os.path.join(pdf_screenshot_dir, f"page_{page_num_in_doc}.jpg")
            img.save(img_path, "JPEG", quality=85)
            saved_pages_map[str(page_num_in_doc)] = img_path
        
        # Replace [PAGE-N] placeholders with actual image links
        markdown_with_images = self.markdown_utils.replace_screenshot_placeholders(
            cleaned_markdown, saved_pages_map, paths['output_dir']
        )
        
        return markdown_with_images

