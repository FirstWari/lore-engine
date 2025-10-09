import os
import logging
import srt
import math
from typing import Dict, Any, Optional
from PIL import Image

# sys.path manipulation removed - use proper Python package imports

from notes_generator.processors.base_processor import BaseNotesProcessor
from notes_generator.constants import VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


class TranscriptNotesProcessor(BaseNotesProcessor):
    """
    Processor for transcript files (SRT) with optional video context.
    
    Handles two scenarios:
    1. SRT-only: Processes subtitles as text chunks
    2. SRT + Video: Processes subtitles with extracted video frames for visual context
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_path: Optional[str] = None
        self.srt_path: Optional[str] = None

    def process(self, file_path: str, output_dir: str, prompt_type: str = None, 
                custom_prompt: str = None, conciseness: str = None, output_format: str = None,
                tools: list = None, video_path: Optional[str] = None, **kwargs) -> None:
        """
        Process a transcript file (SRT) and generate markdown notes.
        
        Args:
            file_path: Path to the SRT file (or video file if video_path is None)
            output_dir: Directory for output files
            prompt_type: Type of prompt to use (defaults to "captions")
            custom_prompt: Custom prompt text
            conciseness: Conciseness level ('short_hand', 'balanced', 'deep_dive')
            video_path: Optional path to the video file. If provided, extracts frames for context.
                       If file_path is a video, this is ignored and the SRT is auto-detected.
            **kwargs: Additional arguments (ignored)
        """
        # Determine if we're processing a video file or an SRT file
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in VIDEO_EXTENSIONS:
            # Processing a video file - find matching SRT
            self.video_path = file_path
            self.srt_path = os.path.splitext(file_path)[0] + '.srt'
            
            if not os.path.exists(self.srt_path):
                logger.warning(f"Skipping video '{os.path.basename(file_path)}': No matching .srt file found at '{self.srt_path}'")
                return
                
            logger.info(f"Processing video with transcript: {os.path.basename(file_path)}")
            
        elif file_ext == '.srt':
            # Processing an SRT file - check for optional video
            self.srt_path = file_path
            
            if video_path and os.path.exists(video_path):
                self.video_path = video_path
                logger.info(f"Processing SRT with video context: {os.path.basename(file_path)}")
            else:
                # SRT-only mode
                self.video_path = None
                logger.info(f"Processing SRT without video: {os.path.basename(file_path)}")
        else:
            logger.error(f"Unsupported file type for TranscriptNotesProcessor: {file_ext}")
            return

        # Set default prompt type for transcripts
        if prompt_type is None:
            prompt_type = "captions"

        # Choose the appropriate processing method
        if self.video_path:
            self._process_with_video(self.srt_path, output_dir, prompt_type, custom_prompt, 
                                    conciseness, output_format, tools)
        else:
            self._process_srt_only(self.srt_path, output_dir, prompt_type, custom_prompt, 
                                   conciseness, output_format, tools)

    def _process_srt_only(self, srt_path: str, output_dir: str, 
                          prompt_type: str, custom_prompt: str, conciseness: str = None,
                          output_format: str = None, tools: list = None) -> None:
        """Process SRT file without video context (text-only)."""
        
        def srt_chunk_processor(source_path: str, user_prompt: str, paths: Dict[str, str]):
            """Generator that yields SRT chunks for processing."""
            subtitles_per_chunk = self.config.get("lines_per_chunk")
            
            all_subtitles = self.content_extractor.parse_srt_content(source_path)
            total_subtitles = len(all_subtitles)
            if total_subtitles == 0:
                logger.warning(f"No text content found in {source_path}. Aborting.")
                return

            logger.info(f"Parsed {total_subtitles} subtitles from SRT file.")

            for i in range(0, total_subtitles, subtitles_per_chunk):
                chunk_subtitles = all_subtitles[i:i + subtitles_per_chunk]
                if not chunk_subtitles:
                    break

                # Extract text content from subtitles
                text_chunk = "\n".join(sub.content.strip() for sub in chunk_subtitles)
                
                # Get timestamp range for the chunk
                start_time = chunk_subtitles[0].start
                end_time = chunk_subtitles[-1].end
                
                start_sub_index = i + 1
                end_sub_index = i + len(chunk_subtitles)
                
                chunk_info = f"subtitles {start_sub_index}-{end_sub_index} (Time: {start_time} - {end_time})"
                
                chunk_data = {
                    'text': text_chunk,
                    'start_time': start_time,
                    'end_time': end_time,
                    'mode': 'srt_only'
                }
                
                yield chunk_data, chunk_info

        self._process_source(srt_path, output_dir, prompt_type, custom_prompt, srt_chunk_processor, 
                            conciseness, output_format, tools)

    def _process_with_video(self, srt_path: str, output_dir: str, 
                           prompt_type: str, custom_prompt: str, conciseness: str = None,
                           output_format: str = None, tools: list = None) -> None:
        """Process SRT file with video context (text + frames)."""
        
        def video_chunk_processor(source_path: str, user_prompt: str, paths: Dict[str, str]):
            """Generator that yields video chunks for processing."""
            subtitles_per_chunk = self.config.get("lines_per_chunk")
            
            # Create a dedicated directory for this video's screenshots
            base_screenshot_dir = os.path.join(paths['output_dir'], "notes_screenshots")
            screenshot_dir = os.path.join(
                base_screenshot_dir, 
                f"{paths['fs_safe_prefix']}_{paths['fs_safe_name']}_screenshots"
            )
            os.makedirs(screenshot_dir, exist_ok=True)

            try:
                # Reuse the existing SRT parsing logic (DRY principle!)
                subtitles = self.content_extractor.parse_srt_content(srt_path)

                if not subtitles:
                    logger.warning(f"SRT file '{srt_path}' is empty or invalid. Aborting.")
                    return

                total_subs = len(subtitles)
                logger.info(f"Parsed {total_subs} subtitles from SRT file.")

                global_seen_hashes = set()  # Track unique frames across the whole video

                for i in range(0, total_subs, subtitles_per_chunk):
                    chunk_subs = subtitles[i:i + subtitles_per_chunk]
                    if not chunk_subs:
                        break

                    start_sub_index = i + 1
                    end_sub_index = i + len(chunk_subs)

                    # Get text content from the chunk
                    text_chunk = "\n".join(sub.content.strip() for sub in chunk_subs)

                    # Get timestamps for the chunk
                    start_time_ms = chunk_subs[0].start.total_seconds() * 1000
                    end_time_ms = chunk_subs[-1].end.total_seconds() * 1000
                    
                    chunk_info = f"subtitles {start_sub_index}-{end_sub_index} (Time: {start_time_ms/1000:.2f}s - {end_time_ms/1000:.2f}s)"
                    
                    # Extract diverse frames from this chunk
                    duration_minutes = (end_time_ms - start_time_ms) / 60000
                    screenshots_per_minute = self.config.get("screenshots_per_minute")
                    num_to_select = math.ceil(duration_minutes * screenshots_per_minute)
                    
                    similarity_threshold = self.config.get("hash_similarity_threshold")
                    min_diversity_threshold = self.config.get("min_diversity_threshold")
                    saved_frames_map, global_seen_hashes = self.content_extractor.extract_diverse_frames(
                        self.video_path, start_time_ms, end_time_ms, screenshot_dir, 
                        global_seen_hashes, 
                        num_to_select=num_to_select,
                        similarity_threshold=similarity_threshold,
                        min_diversity_threshold=min_diversity_threshold
                    )

                    # Load the saved images into PIL objects for the API call
                    image_chunk = []
                    if saved_frames_map:
                        for frame_path in saved_frames_map.values():
                            try:
                                image_chunk.append(Image.open(frame_path))
                            except Exception as e:
                                logger.error(f"Failed to load saved frame for API: {frame_path}. Error: {e}")

                    # Construct the full prompt for this chunk
                    available_screenshots_text = "\n".join([f"- [SCREENSHOT-{ts}]" for ts in saved_frames_map.keys()])
                    
                    full_prompt = (
                        f"{user_prompt}\n\n"
                        "**AVAILABLE SCREENSHOTS:**\n"
                        f"{available_screenshots_text}\n\n"
                        "--- END OF INSTRUCTIONS ---\n\n"
                        "Please generate notes for the following transcript chunk, using the provided screenshots for visual context.\n\n"
                        "**TRANSCRIPT CHUNK:**\n\n"
                        f"{text_chunk}"
                    )

                    chunk_data = {
                        'images': image_chunk,
                        'text': text_chunk,
                        'saved_frames_map': saved_frames_map,
                        'full_prompt': full_prompt,
                        'mode': 'video'
                    }
                    
                    yield chunk_data, chunk_info

            except Exception as e:
                logger.error(f"Failed to process video {self.video_path}: {e}")

        # Use video path as the source for display purposes
        self._process_source(self.video_path, output_dir, prompt_type, custom_prompt, video_chunk_processor,
                            conciseness, output_format, tools)

    def _process_single_chunk(self, chunk_data: Dict[str, Any], user_prompt: str, paths: Dict[str, str]) -> str:
        """
        Process a single transcript chunk (either text-only or with video).
        
        Args:
            chunk_data: Dictionary containing chunk data and processing mode
            user_prompt: The prompt to use for LLM interaction
            paths: Dictionary containing output path information
            
        Returns:
            str: Processed markdown content
        """
        mode = chunk_data.get('mode')
        
        if mode == 'srt_only':
            return self._process_srt_chunk(chunk_data, user_prompt)
        elif mode == 'video':
            return self._process_video_chunk(chunk_data, user_prompt, paths)
        else:
            raise ValueError(f"Unknown processing mode: {mode}")

    def _process_srt_chunk(self, chunk_data: Dict[str, Any], user_prompt: str) -> str:
        """Process an SRT chunk with text content and timestamp context."""
        text_chunk = chunk_data['text']
        start_time = chunk_data['start_time']
        end_time = chunk_data['end_time']
        
        # Format timestamps for human-readable display
        formatted_text = (
            f"[Timestamp: {start_time} - {end_time}]\n\n"
            f"{text_chunk}"
        )
        
        # Generate markdown from text with timestamp context
        markdown_output, self.llm_interaction.last_request_time = self.llm_interaction.generate_markdown_from_text(
            formatted_text, user_prompt
        )
        cleaned_markdown = self.markdown_utils.clean_markdown(markdown_output)
        
        return cleaned_markdown

    def _process_video_chunk(self, chunk_data: Dict[str, Any], user_prompt: str, paths: Dict[str, str]) -> str:
        """Process a video chunk with images and text content."""
        image_chunk = chunk_data['images']
        saved_frames_map = chunk_data['saved_frames_map']
        full_prompt = chunk_data['full_prompt']
        
        try:
            raw_markdown, self.llm_interaction.last_request_time = self.llm_interaction.generate_markdown_notes(
                image_chunk, full_prompt
            )
            
            # Replace placeholders with actual image links
            markdown_with_images = self.markdown_utils.replace_screenshot_placeholders(
                raw_markdown, saved_frames_map, paths['output_dir']
            )
            
            cleaned_markdown = self.markdown_utils.clean_markdown(markdown_with_images)
            
            return cleaned_markdown
            
        finally:
            # Close the PIL images to free up resources
            for img in image_chunk:
                img.close()

