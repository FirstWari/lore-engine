import argparse
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    # Try relative imports first (for running from src directory)
    from config_utils import Config
    from notes_generator.main_notes_generator import NotesGenerator
    from notes_generator.constants import VIDEO_EXTENSIONS
    from user_input import get_streamlined_user_input
    from logging_utils import setup_unicode_logging
except ImportError:
    # Fall back to absolute imports (for running from root or importing from tests)
    from src.config_utils import Config
    from src.notes_generator.main_notes_generator import NotesGenerator
    from src.notes_generator.constants import VIDEO_EXTENSIONS
    from src.user_input import get_streamlined_user_input
    from src.logging_utils import setup_unicode_logging

# Configure logging with centralized utility
setup_unicode_logging()
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Convert PDF slides or notes to enhanced markdown")
    parser.add_argument("input", nargs='?', default=None, help="Path to the input PDF/SRT/Video file or a directory. If omitted, runs in interactive mode.")

    # Input/output options
    parser.add_argument("--output", help="Output directory for markdown files")
    parser.add_argument("--start-page", type=int, default=0, help="Page number to start processing from (0-indexed, for PDFs only)")

    # Configuration
    parser.add_argument("--config", help="Path to configuration JSON file")
    parser.add_argument("--pages-per-chunk", type=int, help="Number of pages to process in each API call (for PDFs, overrides config)")
    parser.add_argument("--lines-per-chunk", type=int, help="Number of subtitles to process in each API call (for SRT/Video, overrides config)")
    parser.add_argument("--screenshots-per-minute", type=float, help="Maximum number of screenshots per minute of video (fractions are allowed).")
    parser.add_argument("--hash-similarity-threshold", type=int, help="Perceptual hash distance to consider images duplicates (lower is stricter).")
    parser.add_argument("--min-diversity-threshold", type=int, help="Minimum hash distance required for a new diverse screenshot to be included.")
    parser.add_argument("--prompt-type", choices=["slides", "handwritten", "custom", "captions"],
                      help="Type of content being processed (overrides config)")
    parser.add_argument("--custom-prompt", help="Path to a file containing a custom prompt (overrides config)")
    parser.add_argument("--output-prefix", help="Prefix for output files (overrides config)")
    parser.add_argument("--model", help="Gemini model to use (overrides config)")

    # API configuration
    parser.add_argument("--api-key", help="Gemini API key(s). Separate multiple keys with commas. Overrides config and environment variables.")

    # Interactive and default options
    parser.add_argument("-d", "--defaults", action="store_true", help="Run with default settings and skip interactive prompts if possible.")
    parser.add_argument("-y", "--yes", action="store_true", help="Answer yes to all prompts (for fully automated default behavior).")

    return parser.parse_args()

def main():
    """Main function to run the script."""
    args = parse_arguments()

    # If not running with defaults or 'yes' flag, use streamlined interactive input
    if not (args.defaults or args.yes):
        config = get_streamlined_user_input()
        # Convert config dict to args-like object for compatibility
        args.input = config['input_path']  # Use the original input path
        args.output = config['output_dir']
        # Store additional config for later use
        args.streamlined_config = config
    
    # Validate that input was provided either via argument or interactively
    if not args.input:
        logger.error("An input file or directory is required.")
        return

    # Determine processing mode if not already set by interactive flow
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input path does not exist: {args.input}")
        return
    
    processing_mode = ''
    if input_path.is_dir():
        processing_mode = 'batch'
    elif input_path.is_file():
        ext = input_path.suffix.lower()
        if ext == '.pdf':
            processing_mode = 'pdf'
        elif ext == '.srt':
            processing_mode = 'srt'
        elif ext in VIDEO_EXTENSIONS:
            processing_mode = 'video'
        else:
            logger.error(f"Unsupported file type: {ext}")
            return
            
    if not args.output:
        args.output = str(input_path.parent) if input_path.is_file() else str(input_path)
        logger.info(f"Output directory not specified, defaulting to '{args.output}'")
    
    try:
        custom_prompt = None
        if args.custom_prompt and os.path.exists(args.custom_prompt):
            with open(args.custom_prompt, 'r') as f:
                custom_prompt = f.read()

        # Initialize Config and apply overrides from command-line arguments
        config_instance = Config(args.config)
        config_instance.update_from_args(args)

        # Initialize NotesGenerator with the configured Config object
        generator = NotesGenerator(config=config_instance)

        # Get prompt_type and additional params from streamlined config if available
        if hasattr(args, 'streamlined_config') and args.streamlined_config:
            prompt_type = args.streamlined_config['mode']
            # Also update config with streamlined params for workers
            config_instance.config['conciseness'] = args.streamlined_config['conciseness']
            config_instance.config['output_format'] = args.streamlined_config['output_format']
            config_instance.config['tools'] = args.streamlined_config['tools']
        else:
            prompt_type = args.prompt_type or config_instance.get("prompt_type")

        # Route to the correct processor
        if processing_mode == 'pdf':
            logger.info(f"Processing single PDF file: {args.input}")
            generator.process_pdf(
                pdf_path=args.input, output_dir=args.output, start_page=args.start_page,
                prompt_type=prompt_type, custom_prompt=custom_prompt
            )
        elif processing_mode == 'srt':
            logger.info(f"Processing single SRT file: {args.input}")
            generator.process_srt(
                srt_path=args.input, output_dir=args.output,
                prompt_type=prompt_type, custom_prompt=custom_prompt
            )
        elif processing_mode == 'video':
            logger.info(f"Processing single video file: {args.input}")
            generator.process_video(
                video_path=args.input, output_dir=args.output,
                prompt_type=prompt_type, custom_prompt=custom_prompt
            )
        elif processing_mode == 'batch':
            logger.info(f"Processing directory in batch mode: {args.input}")
            generator.batch_process(
                input_dir=args.input, output_dir=args.output, start_page=args.start_page,
                prompt_type=prompt_type, custom_prompt=custom_prompt
            )

    except Exception as e:
        logger.error(f"An unexpected application error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()