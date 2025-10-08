"""
Centralized logging configuration for consistent setup across main process and workers.
"""
import logging
import sys


def setup_unicode_logging(log_file: str = "notesmaker.log", level: int = logging.INFO):
    """
    Setup logging with proper Unicode support for both main process and worker processes.
    
    This function configures logging to handle Unicode characters properly across different
    platforms, particularly Windows. It creates both file and console handlers with UTF-8 encoding.
    
    Args:
        log_file: Path to the log file (default: "notesmaker.log")
        level: Logging level (default: logging.INFO)
    """
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    # Configure UTF-8 encoding for console output on Windows
    if sys.platform.startswith('win'):
        import io
        try:
            # Try to reconfigure existing streams for UTF-8
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            # If reconfigure fails, wrap the streams
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    # Configure logging with UTF-8 support
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )

