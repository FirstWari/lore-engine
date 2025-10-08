"""
Constants used throughout the notes generation system.

Centralized magic numbers for easier maintenance and configuration.
"""

# ===== IMAGE PROCESSING =====

# JPEG quality settings (0-100, higher = better quality but larger file size)
PDF_RENDER_QUALITY = 80          # Quality for PDF page renders
VIDEO_FRAME_QUALITY = 85         # Quality for video frame extraction
IMAGE_COMPRESSION_QUALITY = 80   # General image compression quality

# PDF rendering scale (higher = better resolution but larger file size)
PDF_RENDER_SCALE = 2             # Multiplier for PDF render resolution

# ===== VIDEO PROCESSING =====

# Perceptual hash settings for frame diversity
PHASH_SIZE = 8                   # Size of perceptual hash matrix
PHASH_HIGHFREQ_FACTOR = 4        # High frequency factor for phash

# Frame extraction
DEFAULT_NUM_SAMPLES = 15         # Default number of frames to extract per video chunk

# ===== API LIMITS =====

# Gemini API image size threshold (bytes)
FILE_API_THRESHOLD_MB = 19       # Use File API if total images > this many MB
FILE_API_THRESHOLD_BYTES = FILE_API_THRESHOLD_MB * 1024 * 1024

# ===== VIDEO READING =====

# Safety timeout for video frame reading (seconds)
VIDEO_READ_TIMEOUT_SECONDS = 5   # Max time to wait for a single frame read

# Supported video file extensions
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']


