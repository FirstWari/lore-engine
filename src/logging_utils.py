"""
Centralized logging configuration for consistent setup across main process and workers.
"""
import logging
import sys
import os
import warnings


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
    
    # Suppress noisy third-party library warnings
    _suppress_third_party_warnings()


def _suppress_third_party_warnings():
    """
    Suppress verbose warnings from third-party libraries that clutter the logs.
    
    Suppresses:
    - FFmpeg/video-reader-rs warnings (handled via file descriptor redirection in content_extractor.py)
    - gRPC ALTS credentials warnings (Google API client)
    - absl logging warnings
    """
    # Suppress absl logging warnings (used by Google libraries)
    # Must import and configure absl BEFORE any Google library imports
    try:
        # Prevent absl from printing to stderr
        import absl.logging
        # Use Python logging instead of absl's own logging
        absl.logging.use_python_logging()
        # Set to ERROR level to suppress INFO/WARNING
        absl_logger = logging.getLogger('absl')
        absl_logger.setLevel(logging.ERROR)
    except ImportError:
        pass
    
    # Set gRPC logger to ERROR level
    logging.getLogger('grpc').setLevel(logging.ERROR)
    logging.getLogger('google').setLevel(logging.ERROR)
    logging.getLogger('google.api_core').setLevel(logging.ERROR)
    logging.getLogger('google.auth').setLevel(logging.ERROR)
    
    # Suppress general Python warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    warnings.filterwarnings('ignore', category=UserWarning)

