import google.generativeai as genai
import time
import logging
import os
import io
import tempfile
import base64
from typing import List, Dict, Tuple, Optional, Union
from PIL import Image

# sys.path manipulation removed - use proper Python package imports

from config_utils import Config
from notes_generator.constants import FILE_API_THRESHOLD_BYTES

logger = logging.getLogger(__name__)

class LLMInteraction:
    def __init__(self, config: Config, api_key: str):
        if not api_key:
            raise ValueError("LLMInteraction requires a valid API key for initialization.")
        self.config = config
        self.api_key = api_key
        self.last_request_time = 0
        self.model = None
        self.chat_session = None
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5)
        self.setup_genai()

    def setup_genai(self):
        """Setup Google Generative AI API with the specific API key."""
        try:
            genai.configure(api_key=self.api_key)

            generation_config = {
                "temperature": self.config.get("temperature"),
                "top_p": self.config.get("top_p"),
                "top_k": self.config.get("top_k"),
                "max_output_tokens": self.config.get("max_output_tokens"),
                "response_mime_type": "text/plain",
            }

            self.model = genai.GenerativeModel(
                model_name=self.config.get("model_name"),
                generation_config=generation_config,
            )

            self.chat_session = self.model.start_chat(history=[])
            # To avoid clutter, we can skip logging this for every worker
            # logger.info(f"Initialized model: {self.config.get('model_name')} for a worker.")
        except Exception as e:
            logger.error(f"Failed to set up Generative AI for a worker: {e}")
            raise

    def _encode_images_once(self, pil_images_list: List[Image.Image]) -> Tuple[List[bytes], int]:
        """
        Encode all images to JPEG once and return bytes + total size.
        OPTIMIZATION: Prevents double encoding (was encoding to check size, then encoding again to send).
        
        Returns:
            Tuple of (list of JPEG bytes, total size in bytes)
        """
        encoded_images = []
        total_size = 0
        
        for img in pil_images_list:
            bio = io.BytesIO()
            img.save(bio, format='JPEG')
            image_bytes = bio.getvalue()
            encoded_images.append(image_bytes)
            total_size += len(image_bytes)
        
        return encoded_images, total_size

    def _prepare_inline_images_from_bytes(self, encoded_images: List[bytes]) -> List[dict]:
        """Convert encoded JPEG bytes to inline image parts as dictionaries."""
        image_parts = []
        for image_bytes in encoded_images:
            encoded_string = base64.b64encode(image_bytes).decode('utf-8')
            image_part = {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": encoded_string
                }
            }
            image_parts.append(image_part)
        return image_parts

    def generate_markdown_notes(self, pil_images_list: List[Image.Image], user_prompt: str, force_file_api: bool = False) -> Tuple[str, float]:
        """
        Sends PIL Image objects to Gemini, handles rate limiting, and returns Markdown.
        
        Args:
            pil_images_list: List of PIL Image objects
            user_prompt: The prompt to send to the model
            force_file_api: Force using File API even for small images
            
        Returns:
            Tuple of (generated markdown text, request timestamp)
        """
        # OPTIMIZATION: Encode images once, not twice
        encoded_images, total_size = self._encode_images_once(pil_images_list)
        use_file_api = force_file_api or total_size > FILE_API_THRESHOLD_BYTES

        if use_file_api:
            return self._generate_with_file_api(pil_images_list, user_prompt)
        else:
            return self._generate_with_inline_images_cached(encoded_images, user_prompt)

    def _generate_with_inline_images_cached(self, encoded_images: List[bytes], user_prompt: str) -> Tuple[str, float]:
        """Generate markdown using pre-encoded image data (no double encoding!)."""
        try:
            contents = [user_prompt]
            contents.extend(self._prepare_inline_images_from_bytes(encoded_images))

            for attempt in range(self.max_retries):
                try:
                    # Rate Limiting
                    request_interval = self.config.get("request_interval")
                    elapsed_time = time.time() - self.last_request_time
                    if elapsed_time < request_interval:
                        wait_time = request_interval - elapsed_time
                        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                        time.sleep(wait_time)

                    response = self.chat_session.send_message(contents)
                    current_request_time = time.time()
                    return response.text, current_request_time
                except Exception as e:
                    logger.error(f"Error during inline generation (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise  # Re-raise if all retries fail

        except Exception as e:
            logger.error(f"Error during inline generation: {e}")
            raise

    def _generate_with_file_api(self, pil_images_list: List[Image.Image], user_prompt: str) -> Tuple[str, float]:
        """Generate markdown using File API for images."""
        contents = [user_prompt]
        file_references = []
        temp_files = []

        try:
            # Save images to temporary files
            for img in pil_images_list:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                    img.save(tmp_file, format="JPEG")
                    temp_image_path = tmp_file.name
                    temp_files.append(temp_image_path)

            # Upload images with retry mechanism
            for attempt in range(self.max_retries):
                try:
                    for temp_image_path in temp_files:
                        file_ref = genai.upload_file(path=temp_image_path)
                        file_references.append(file_ref)
                    break  # Break if upload is successful
                except Exception as upload_error:
                    logger.error(f"Error uploading file (attempt {attempt + 1}/{self.max_retries}): {upload_error}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise  # Re-raise if all retries fail

            contents.extend(file_references)

            # Send message to model with retry mechanism
            for attempt in range(self.max_retries):
                try:
                    # Rate Limiting
                    request_interval = self.config.get("request_interval")
                    elapsed_time = time.time() - self.last_request_time
                    if elapsed_time < request_interval:
                        wait_time = request_interval - elapsed_time
                        logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                        time.sleep(wait_time)

                    response = self.chat_session.send_message(contents)
                    current_request_time = time.time()
                    return response.text, current_request_time
                except Exception as e:
                    logger.error(f"Error during generation (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise  # Re-raise if all retries fail

        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise

        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {e}")
    
    def generate_markdown_from_text(self, text_chunk: str, user_prompt: str) -> Tuple[str, float]:
        """Sends a text chunk to Gemini, handles rate limiting, and returns Markdown."""
        contents = [user_prompt, f"Here is the transcript chunk:\n\n{text_chunk}"]
        for attempt in range(self.max_retries):
            try:
                # Rate Limiting
                request_interval = self.config.get("request_interval")
                elapsed_time = time.time() - self.last_request_time
                if elapsed_time < request_interval:
                    wait_time = request_interval - elapsed_time
                    logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)

                # Send message to model
                response = self.chat_session.send_message(contents)
                current_request_time = time.time()
                return response.text, current_request_time
            except Exception as e:
                logger.error(f"Error during text generation (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise  # Re-raise if all retries fail