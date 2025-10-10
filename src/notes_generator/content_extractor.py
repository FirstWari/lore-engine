import pypdfium2 as pdfium
from PIL import Image
import srt
import re
import io
import logging
import os
import sys
from contextlib import contextmanager
from typing import List, Dict, Tuple, Optional

from notes_generator.constants import (
    PDF_RENDER_SCALE,
    PHASH_SIZE,
    PHASH_HIGHFREQ_FACTOR,
    DEFAULT_NUM_SAMPLES
)

# Add imagehash for perceptual hashing
try:
    import imagehash
except ImportError:
    imagehash = None
    logging.getLogger(__name__).warning("imagehash library not found. pip install imagehash")

# Add video_reader-rs for fast video decoding with better memory management
try:
    from video_reader import PyVideoReader
except ImportError:
    PyVideoReader = None
    logging.getLogger(__name__).warning("video-reader-rs library not found. pip install video-reader-rs")

logger = logging.getLogger(__name__)


@contextmanager
def suppress_stderr():
    """
    Context manager to suppress stderr at the file descriptor level.
    
    Useful for suppressing noisy FFmpeg warnings from video_reader-rs (Rust library)
    that writes directly to stderr bypassing Python's logging system.
    """
    # Save original stderr file descriptor
    stderr_fd = sys.stderr.fileno()
    stderr_backup_fd = os.dup(stderr_fd)
    
    try:
        # Redirect stderr to devnull
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, stderr_fd)
        os.close(devnull)
        yield
    finally:
        # Restore original stderr
        os.dup2(stderr_backup_fd, stderr_fd)
        os.close(stderr_backup_fd)


class ContentExtractor:
    def __init__(self):
        pass

    def _calculate_hash_distances(self, candidates, selected_hashes):
        """Helper to calculate the minimum distance of each candidate to the selected set."""
        distances = []
        for cand_hash, _, _ in candidates:
            min_dist = min(cand_hash - sel_hash for sel_hash in selected_hashes)
            distances.append(min_dist)
        return distances
        
    def extract_diverse_frames(self, video_path: str, start_time_ms: float, end_time_ms: float, 
                               output_dir: str, global_seen_hashes: set, num_to_select: int, 
                               similarity_threshold: int, min_diversity_threshold: int,
                               num_candidate_samples: int = 20) -> Tuple[Dict[str, str], set]:
        """
        Samples candidate frames using video_reader-rs (Rust-based fast video decoder with excellent 
        memory management), filters duplicates, and selects up to N frames that each meet a minimum 
        diversity threshold.
        
        Uses video_reader-rs which doesn't allocate memory for the entire video upfront, preventing 
        crashes on large videos and providing better performance than Decord or OpenCV.
        """
        if imagehash is None:
            logger.error("imagehash library is required for diverse frame extraction.")
            return {}, global_seen_hashes
        
        if PyVideoReader is None:
            logger.error("video-reader-rs library is required for fast frame extraction. pip install video-reader-rs")
            return {}, global_seen_hashes
            
        try:
            # Suppress FFmpeg stderr output (noisy warnings about frame properties)
            # FFmpeg writes directly to stderr, bypassing Python logging
            with suppress_stderr():
                vr = PyVideoReader(video_path, threads=0)  # threads=0 means auto (optimal)
        except Exception as e:
            logger.error(f"Could not open video file with video_reader-rs: {video_path}. Error: {e}")
            return {}, global_seen_hashes

        candidate_frames = []
        try:
            # Get video properties
            shape = vr.get_shape()
            total_video_frames = shape[0]  # (num_frames, height, width)
            
            # Get FPS from info dict
            info = vr.get_info()
            fps = float(info.get('fps', 30.0))  # Default to 30 if not available
            
            # Calculate frame indices for the time range
            start_frame_idx = int(start_time_ms / 1000 * fps)
            end_frame_idx = int(end_time_ms / 1000 * fps)
            
            # Clamp to valid range
            start_frame_idx = max(0, min(start_frame_idx, total_video_frames - 1))
            end_frame_idx = max(0, min(end_frame_idx, total_video_frames - 1))
            
            # Calculate duration and sampling parameters
            duration_ms = end_time_ms - start_time_ms
            if duration_ms <= 0 or start_frame_idx >= end_frame_idx:
                # Edge case: no duration, just sample start frame
                try:
                    with suppress_stderr():
                        frame = vr[start_frame_idx]  # Direct indexing
                    pil_image = Image.fromarray(frame)
                    current_hash = imagehash.phash(pil_image, hash_size=PHASH_SIZE, highfreq_factor=PHASH_HIGHFREQ_FACTOR)
                    if not any(current_hash - seen_hash <= similarity_threshold for seen_hash in global_seen_hashes):
                        candidate_frames.append((current_hash, pil_image, start_time_ms))
                except Exception as e:
                    logger.warning(f"Failed to extract frame at {start_frame_idx}: {e}")
            else:
                # Calculate how many frames to sample
                total_frames_in_chunk = end_frame_idx - start_frame_idx
                num_samples = min(num_candidate_samples, total_frames_in_chunk, 100)
                
                if num_samples <= 1:
                    num_samples = 1
                
                # Calculate frame indices to sample (evenly distributed)
                sample_every_n_frames = max(1, total_frames_in_chunk // num_samples)
                frame_indices = [
                    start_frame_idx + i * sample_every_n_frames 
                    for i in range(num_samples)
                    if start_frame_idx + i * sample_every_n_frames < end_frame_idx
                ]
                
                # OPTIMIZATION: Use video_reader-rs's get_batch for efficient frame extraction!
                # This library has excellent memory management and won't crash on large videos
                if frame_indices:
                    try:
                        with suppress_stderr():
                            frames_batch = vr.get_batch(frame_indices)  # Returns numpy array (N, H, W, C)
                        
                        # Process each frame
                        for i, frame_idx in enumerate(frame_indices):
                            frame = frames_batch[i]
                            current_ms = (frame_idx / fps) * 1000
                            
                            # Convert to PIL Image (video_reader-rs returns RGB format by default)
                            pil_image = Image.fromarray(frame)
                            current_hash = imagehash.phash(pil_image, hash_size=PHASH_SIZE, highfreq_factor=PHASH_HIGHFREQ_FACTOR)
                            
                            # Check if too similar to any globally seen hash
                            is_duplicate = False
                            for seen_hash in global_seen_hashes:
                                if current_hash - seen_hash <= similarity_threshold:
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                candidate_frames.append((current_hash, pil_image, current_ms))
                    
                    except Exception as e:
                        logger.error(f"Failed to extract frames batch: {e}")
                        return {}, global_seen_hashes
        
        except Exception as e:
            logger.error(f"Error during frame extraction: {e}")
            return {}, global_seen_hashes
        
        # 2. Select the most diverse frames from the candidates using pruning
        selected_frames = []
        if not candidate_frames:
            return {}, global_seen_hashes

        # Start with the first candidate
        selected_frames.append(candidate_frames.pop(0))

        while len(selected_frames) < num_to_select and candidate_frames:
            # Prune candidates that are too similar to the LAST frame we selected
            last_selected_hash = selected_frames[-1][0]
            candidate_frames = [
                cand for cand in candidate_frames 
                if (cand[0] - last_selected_hash) > similarity_threshold
            ]
            if not candidate_frames:
                break

            # Select the next most diverse frame
            selected_hashes = {h for h, _, _ in selected_frames}
            distances = self._calculate_hash_distances(candidate_frames, selected_hashes)
            
            # Find the best candidate and its distance
            max_distance = max(distances)
            best_candidate_index = distances.index(max_distance)

            # Quality Check: Only add if it meets the minimum diversity threshold
            if max_distance >= min_diversity_threshold:
                selected_frames.append(candidate_frames.pop(best_candidate_index))
            else:
                # If the most diverse candidate isn't different enough, stop.
                logger.info(f"Stopping early: No more frames meet the minimum diversity of {min_diversity_threshold}.")
                break

        # 3. Save the selected frames and update hashes
        saved_frames_map = {}
        chunk_seen_hashes = set()
        for cand_hash, pil_image, ts_ms in selected_frames:
            chunk_seen_hashes.add(cand_hash)
            seconds = int(ts_ms / 1000)
            h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
            timestamp_str = f"{h:02d}-{m:02d}-{s:02d}"
            
            if timestamp_str in saved_frames_map:
                continue

            filename = f"frame_{timestamp_str}.jpg"
            filepath = os.path.join(output_dir, filename)
            pil_image.save(filepath, "JPEG", quality=80)
            saved_frames_map[timestamp_str] = filepath

        if saved_frames_map:
            logger.info(f"Saved {len(saved_frames_map)} most diverse frames to {output_dir}")
            
        # Return the saved frames and the combined set of old and new hashes
        return saved_frames_map, global_seen_hashes.union(chunk_seen_hashes)

    def extract_images_from_pdf(self, pdf_path: str, start_page: int, num_pages: int) -> List[Image.Image]:
        """
        Extract PIL Image objects from a range of pages in a PDF.
        
        OPTIMIZATION: Returns raw RGB PIL images. Compression happens once in llm_interaction.py.
        Previously: Raw PDF → JPEG → PIL → JPEG (double compression, 1.5x slower!)
        Now: Raw PDF → PIL → JPEG (single compression)
        """
        try:
            pdf_doc = pdfium.PdfDocument(pdf_path)
            pil_images_list = []
            total_pages = len(pdf_doc)
            end_page = min(start_page + num_pages, total_pages)

            logger.info(f"Extracting pages {start_page + 1}-{end_page} from {pdf_path} (Total: {total_pages} pages)")

            for page_index in range(start_page, end_page):
                page = pdf_doc.get_page(page_index)
                render_bitmap = page.render(scale=PDF_RENDER_SCALE)
                img = render_bitmap.to_pil()

                # Convert to RGB (required for JPEG encoding later)
                # No intermediate compression - let llm_interaction.py handle it once
                rgb_img = img.convert('RGB')

                pil_images_list.append(rgb_img)
                page.close()

            pdf_doc.close()
            return pil_images_list

        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            raise

    def parse_srt_content(self, srt_path: str) -> List[srt.Subtitle]:
        """
        Parses an SRT file using the srt library and returns a list of Subtitle objects.
        
        Returns:
            List of srt.Subtitle objects containing content, start time, and end time.
        """
        try:
            with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Use srt library to properly parse the file
            subtitles = list(srt.parse(content))
            
            if not subtitles:
                logger.warning(f"No subtitles found in {srt_path}")
                return []
            
            logger.info(f"Successfully parsed {len(subtitles)} subtitles from {srt_path}")
            return subtitles
            
        except srt.SRTParseError as e:
            logger.error(f"Error parsing SRT file {srt_path}: {e}")
            # Return empty list for malformed SRT files
            return []
        except Exception as e:
            logger.error(f"Error parsing SRT file {srt_path}: {e}")
            raise