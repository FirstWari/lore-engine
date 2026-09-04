import os
import logging
import sys
import signal
from typing import List, Tuple, Set, Dict, Any
import multiprocessing
from itertools import cycle

# sys.path manipulation removed - use proper Python package imports

try:
    from config_utils import Config
    from logging_utils import setup_unicode_logging
    from notes_generator.content_extractor import ContentExtractor
    from notes_generator.markdown_utils import MarkdownUtils
    from notes_generator.processors import PDFNotesProcessor, TranscriptNotesProcessor
    from notes_generator.constants import VIDEO_EXTENSIONS
except ImportError:
    from src.config_utils import Config
    from src.logging_utils import setup_unicode_logging
    from src.notes_generator.content_extractor import ContentExtractor
    from src.notes_generator.markdown_utils import MarkdownUtils
    from src.notes_generator.processors import PDFNotesProcessor, TranscriptNotesProcessor
    from src.notes_generator.constants import VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)

#: The Gemini-backed note writer was removed when lore-engine became an
#: extraction-only skill (lore.py). The agent that runs the command writes the notes.
LLM_GENERATION_REMOVED_MESSAGE = (
    "LLM-based note generation was removed: lore-engine is now a single-command "
    "extraction skill. Run `python lore.py <url|video|pdf>` and let your own AI agent "
    "write the notes from results/<title>/ (see SKILL.md)."
)

# File extension constants
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS + ['.pdf', '.srt']

# ===========================
# Worker Process Functions
# ===========================

def worker_init():
    """Initialize worker process to handle interrupts gracefully"""
    # On Windows, we need different handling
    import sys
    if sys.platform != 'win32':
        # Unix: ignore SIGINT in workers
        signal.signal(signal.SIGINT, signal.SIG_IGN)

def process_file_worker(args: Tuple[str, Dict[str, Any], str]) -> bool:
    """
    Worker function that processes a single file. Designed for multiprocessing Pool.
    
    Args:
        args: Tuple of (file_path, config_dict, api_key)
    
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    file_path, config_dict, api_key = args

    # Setup Unicode logging for worker processes using centralized utility
    setup_unicode_logging()

    # Initialize config with the passed dictionary
    config = Config(initial_config=config_dict)

    pid_info = f" (PID: {os.getpid()})"
    
    try:
        logger.info(f"Worker{pid_info} starting: {os.path.basename(file_path)}")

        # Initialize processing components
        llm_interaction = None
        content_extractor = ContentExtractor()
        markdown_utils = MarkdownUtils()

        # Extract processing parameters
        output_dir = config.get("output_dir")
        prompt_type = config.get("prompt_type")
        custom_prompt = config.get("custom_prompt")
        start_page = config.get("start_page", 0)
        conciseness = config.get("conciseness")
        output_format = config.get("output_format")
        tools = config.get("tools")

        # Determine processor type based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            # Use PDFNotesProcessor for PDF files
            processor = PDFNotesProcessor(config, llm_interaction, content_extractor, markdown_utils)
            processor.process(file_path, output_dir, prompt_type, custom_prompt, 
                            conciseness=conciseness, output_format=output_format,
                            tools=tools, start_page=start_page)
            
        elif ext == '.srt' or ext in VIDEO_EXTENSIONS:
            # Use TranscriptNotesProcessor for both SRT and video files
            processor = TranscriptNotesProcessor(config, llm_interaction, content_extractor, markdown_utils)
            processor.process(file_path, output_dir, prompt_type, custom_prompt,
                            conciseness=conciseness, output_format=output_format,
                            tools=tools)
            
        else:
            logger.warning(f"Worker{pid_info} unsupported file type: {ext}")
            return False

        logger.info(f"Worker{pid_info} completed: {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        logger.error(f"Worker{pid_info} failed on {os.path.basename(file_path)}: {e}", exc_info=True)
        return False


# ===========================
# NotesGenerator Class
# ===========================

class NotesGenerator:
    """
    Main class for generating notes from PDFs, videos, and SRT files.
    Supports both single-file and batch processing with parallel workers.
    """
    
    def __init__(self, config: Config):
        self.config = config

    # ===========================
    # Helper Methods
    # ===========================
    
    def _find_supported_files(self, input_dir: str) -> List[str]:
        """
        Find all supported files in the input directory.
        
        Args:
            input_dir: Directory to search for files
            
        Returns:
            List of file paths
        """
        supported_files = []
        for root, _, files in os.walk(input_dir):
            # Skip screenshot directories
            if "notes_screenshots" in root:
                continue
                
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    supported_files.append(os.path.join(root, file))
        
        return supported_files
    
    def _determine_primary_tasks(self, all_files: List[str]) -> List[str]:
        """
        Determine which files should be processed as primary tasks.
        
        - Videos are primary tasks (workers will find matching SRT files)
        - SRT files without matching videos are primary tasks
        - PDFs are always primary tasks
        
        Args:
            all_files: List of all supported files found
            
        Returns:
            List of files to process as primary tasks
        """
        file_set = {f.lower() for f in all_files}
        primary_tasks = []
        
        for file_path in all_files:
            base_name, ext = os.path.splitext(file_path.lower())

            if ext in VIDEO_EXTENSIONS:
                primary_tasks.append(file_path)
                
            elif ext == '.srt':
                # Only process SRT if no corresponding video exists
                has_matching_video = any(
                    f"{base_name}{video_ext}" in file_set 
                    for video_ext in VIDEO_EXTENSIONS
                )
                if not has_matching_video:
                    logger.info(f"Found orphan SRT (no video): {os.path.basename(file_path)}")
                    primary_tasks.append(file_path)
                    
            elif ext == '.pdf':
                primary_tasks.append(file_path)
        
        return primary_tasks
    
    def _prepare_config_dict(self, output_dir: str, prompt_type: str, 
                            custom_prompt: str, **kwargs) -> Dict[str, Any]:
        """Prepare configuration dictionary for workers."""
        config_dict = self.config.config.copy()
        config_dict.update({
            "output_dir": output_dir,
            "prompt_type": prompt_type,
            "custom_prompt": custom_prompt,
            **kwargs  # Include any additional parameters like start_page
        })
        return config_dict
    
    # ===========================
    # Batch Processing
    # ===========================
    
    def _llm_api_keys(self) -> List[str]:
        """Return LLM API keys, or ``[]`` with a clear error once generation is unavailable.

        ``Config.get_api_keys`` no longer exists after the extraction-only rewrite, so the
        legacy CLI path used to die with an ``AttributeError`` deep inside the
        worker. Fail here, once, with a message that points at lore.py / SKILL.md.
        """
        getter = getattr(self.config, "get_api_keys", None)
        keys = getter() if callable(getter) else []
        if not keys:
            logger.error(LLM_GENERATION_REMOVED_MESSAGE)
            return []
        return list(keys)

    def batch_process(self, input_dir: str, output_dir: str, start_page: int = 0,
                      prompt_type: str = None, custom_prompt: str = None) -> None:
        """
        Process all supported files in a directory in parallel using worker pool.
        Each worker is assigned its own API key in round-robin fashion.
        
        Args:
            input_dir: Directory containing files to process
            output_dir: Directory for output files
            start_page: Starting page for PDF processing
            prompt_type: Type of prompt to use
            custom_prompt: Custom prompt text
        """
        api_keys = self._llm_api_keys()
        if not api_keys:
            return
        
        # Find all supported files
        all_supported_files = self._find_supported_files(input_dir)
        
        # Determine primary tasks
        tasks_to_process = self._determine_primary_tasks(all_supported_files)
        
        if not tasks_to_process:
            logger.warning(f"No tasks found in {input_dir}. Nothing to process.")
            return

        logger.info(f"Found {len(tasks_to_process)} tasks to process")
        logger.info(f"Starting batch processing with {len(api_keys)} parallel workers")
        
        # Prepare configuration for workers
        config_dict = self._prepare_config_dict(output_dir, prompt_type, custom_prompt, start_page=start_page)
        
        # Create task arguments with round-robin API key assignment
        tasks = [
            (file_path, config_dict, api_key) 
            for file_path, api_key in zip(tasks_to_process, cycle(api_keys))
        ]

        # Process files in parallel with proper Ctrl+C handling (Windows-compatible)
        pool = None
        try:
            pool = multiprocessing.Pool(processes=len(api_keys), initializer=worker_init)
            
            # Use map_async with timeout to allow Ctrl+C interruption on Windows
            result = pool.map_async(process_file_worker, tasks)
            
            # Wait with timeout to allow KeyboardInterrupt to be caught
            # This is the key for Windows - blocking map() ignores Ctrl+C
            results = result.get(timeout=999999)  # Very long timeout, but interruptible
            
            # Report results
            successful = sum(1 for r in results if r)
            logger.info(f"Batch processing complete: {successful}/{len(tasks_to_process)} succeeded")
            
        except KeyboardInterrupt:
            print("\n" + "="*70)
            print("⚠️  CTRL+C DETECTED")
            print("="*70)
            print("\nNote: On Windows, workers making API calls cannot be interrupted cleanly.")
            print("The workers will finish their current API call, then stop.")
            print("\nIf you need to stop immediately:")
            print("  - Close this terminal window")
            print("  - Or wait ~30 seconds for current API calls to timeout")
            print("="*70 + "\n")
            
            if pool:
                pool.terminate()
                pool.join()
            logger.info("Termination requested. Workers will stop after current operations.")
            return  # Return instead of raise to avoid stack trace
        except Exception as e:
            logger.error(f"Error during batch processing: {e}")
            if pool:
                pool.terminate()
                pool.join()
            raise
        finally:
            if pool:
                pool.close()
                pool.join()

    # ===========================
    # Single File Processing
    # ===========================
    
    def _process_single_file(self, file_path: str, output_dir: str, 
                            file_type: str, prompt_type: str = None, 
                            custom_prompt: str = None, **kwargs) -> bool:
        """
        Process a single file with API key retry logic.
        
        This method prepares the configuration, attempts processing with each available
        API key in sequence, and returns the result. If one API key fails, it tries the
        next one until all keys are exhausted or processing succeeds.
        
        Args:
            file_path: Path to the file to process
            output_dir: Directory for output files
            file_type: Type of file (for logging purposes)
            prompt_type: Type of prompt to use
            custom_prompt: Custom prompt text
            **kwargs: Additional processor-specific parameters (e.g., start_page)
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        api_keys = self._llm_api_keys()
        if not api_keys:
            return False

        # Prepare config for the worker
        config_dict = self._prepare_config_dict(output_dir, prompt_type, custom_prompt, **kwargs)
        
        filename = os.path.basename(file_path)

        # Try each API key once in sequence
        for idx, api_key in enumerate(api_keys, 1):
            key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"
            
            try:
                if len(api_keys) > 1:
                    logger.info(f"Attempting with API key {idx}/{len(api_keys)} (...{key_suffix})")
                
                success = process_file_worker((file_path, config_dict, api_key))
                
                if success:
                    logger.info(f"Successfully processed {file_type}: {filename}")
                    return True
                else:
                    logger.warning(f"Processing failed with API key ...{key_suffix}")
                    
            except Exception as e:
                logger.error(f"Error with API key ...{key_suffix}: {e}")

        logger.error(f"Failed to process {file_type} '{filename}' with all {len(api_keys)} available API key(s)")
        return False
    
    def process_pdf(self, pdf_path: str, output_dir: str, start_page: int = 0,
                    prompt_type: str = None, custom_prompt: str = None) -> None:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory for output files
            start_page: Starting page number
            prompt_type: Type of prompt to use
            custom_prompt: Custom prompt text
        """
        self._process_single_file(
            pdf_path, output_dir, "PDF", prompt_type, custom_prompt, 
            start_page=start_page
        )

    def process_srt(self, srt_path: str, output_dir: str,
                    prompt_type: str = None, custom_prompt: str = None) -> None:
        """
        Process a single SRT subtitle file.
        
        Args:
            srt_path: Path to the SRT file
            output_dir: Directory for output files
            prompt_type: Type of prompt to use
            custom_prompt: Custom prompt text
        """
        self._process_single_file(srt_path, output_dir, "SRT", prompt_type, custom_prompt)

    def process_video(self, video_path: str, output_dir: str,
                      prompt_type: str = None, custom_prompt: str = None) -> None:
        """
        Process a single video file (requires matching SRT file).
        
        Args:
            video_path: Path to the video file
            output_dir: Directory for output files
            prompt_type: Type of prompt to use
            custom_prompt: Custom prompt text
        """
        self._process_single_file(video_path, output_dir, "video", prompt_type, custom_prompt)