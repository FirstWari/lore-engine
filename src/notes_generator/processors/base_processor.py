import os
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any

# sys.path manipulation removed - use proper Python package imports

try:
    from config_utils import Config
    from prompt_builder import PromptBuilder
    from notes_generator.content_extractor import ContentExtractor
    from notes_generator.markdown_utils import MarkdownUtils
except ImportError:
    from src.config_utils import Config
    from src.prompt_builder import PromptBuilder
    from src.notes_generator.content_extractor import ContentExtractor
    from src.notes_generator.markdown_utils import MarkdownUtils

logger = logging.getLogger(__name__)


class BaseNotesProcessor(ABC):
    """
    Abstract base class for all note processors.
    
    This class encapsulates the common logic for processing various content types,
    including output file management, chunk processing, and logging.
    """
    
    def __init__(self, config: Config, llm_interaction: Any = None, 
                 content_extractor: ContentExtractor = None, markdown_utils: MarkdownUtils = None):
        self.config = config
        self.llm_interaction = llm_interaction
        self.content_extractor = content_extractor or ContentExtractor()
        self.markdown_utils = markdown_utils or MarkdownUtils()

    # ===========================
    # Common Helper Methods
    # ===========================
    
    def _prepare_output_paths(self, source_path: str, output_dir: str) -> Dict[str, str]:
        """Prepare output directory and generate filesystem-safe names."""
        os.makedirs(output_dir, exist_ok=True)
        
        original_name = os.path.splitext(os.path.basename(source_path))[0]
        output_prefix = self.config.get("output_prefix") or "refined"
        
        # Sanitize for filesystem-friendly names
        fs_safe_name = original_name.replace(' ', '_')
        fs_safe_prefix = output_prefix.replace(' ', '_')
        
        # Create a clean, human-readable title for the markdown content
        display_title = re.sub('[-_]', ' ', original_name).title()
        display_title = re.sub(' +', ' ', display_title)
        
        return {
            'original_name': original_name,
            'fs_safe_name': fs_safe_name,
            'fs_safe_prefix': fs_safe_prefix,
            'display_title': display_title,
            'output_dir': output_dir
        }

    def _create_output_file(self, paths: Dict[str, str], file_counter: int) -> str:
        """Create a new output markdown file with header."""
        output_file = os.path.join(
            paths['output_dir'], 
            f"{paths['fs_safe_prefix']}_{paths['fs_safe_name']}_part{file_counter}.md"
        )
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {paths['display_title']} - Part {file_counter}\n\n")
        
        return output_file

    def _log_processing_start(self, source_path: str, output_file: str, prompt_type: str):
        """Log the start of processing with common information."""
        logger.info(f"Processing {source_path}")
        logger.info(f"Output to: {output_file}")
        logger.info(f"Using prompt type: {prompt_type}")

    def _log_chunk_progress(self, chunk_info: str):
        """Log progress for current chunk being processed."""
        logger.info(f"Processing {chunk_info}...")

    def _log_content_preview(self, content: str):
        """Log a preview of the generated content."""
        preview = content[:150] + "..." if len(content) > 150 else content
        logger.info(f"Generated content preview: {preview}")

    # ===========================
    # Template Method Pattern
    # ===========================
    
    def _process_source(self, source_path: str, output_dir: str, prompt_type: str,
                       custom_prompt: str, chunk_processor, conciseness: str = None,
                       output_format: str = None, tools: list = None) -> None:
        """
        Template method that handles the common processing flow for all source types.
        
        Args:
            source_path: Path to the source file
            output_dir: Directory for output files
            prompt_type: Type of prompt to use (mode)
            custom_prompt: Custom prompt if provided
            chunk_processor: Generator function that yields (chunk_data, chunk_info) tuples
            conciseness: Conciseness level to use (optional)
            output_format: Output format ('notes', 'practice_problems', 'formula_sheet')
            tools: List of tool IDs to enable (if None, uses default set)
        """
        api_call_limit_per_file = self.config.get("api_call_limit_per_file")
        
        # Common setup
        paths = self._prepare_output_paths(source_path, output_dir)
        output_file_counter = 1
        output_markdown_file = self._create_output_file(paths, output_file_counter)
        
        api_call_counter = 0
        
        # --- PROMPT BUILDING LOGIC ---
        prompt_builder = PromptBuilder()
        
        if prompt_type == 'custom' and custom_prompt:
            user_prompt = prompt_builder.with_custom_content(custom_prompt).build()
        else:
            # Get defaults from config if not provided
            conciseness_level = conciseness or self.config.get('conciseness', 'balanced')
            output_format_type = output_format or 'notes'
            
            # Build the prompt with the 4-layer architecture
            prompt_builder_chain = (prompt_builder
                           .with_base_instructions()
                           .with_mode(prompt_type)
                           .with_conciseness(conciseness_level)
                           .with_output_format(output_format_type))
            
            # Add tools - use provided list or default set
            if tools is not None:
                # Use provided tools from streamlined input
                for tool in tools:
                    prompt_builder_chain = prompt_builder_chain.with_tool(tool)
            else:
                # Fallback to old behavior for backward compatibility
                prompt_builder_chain = (prompt_builder_chain
                    .with_tool('tables')
                    .with_tool('mermaid_diagrams')
                    .with_tool('screenshots'))
                
                if conciseness_level in ['balanced', 'deep_dive']:
                    prompt_builder_chain = prompt_builder_chain.with_tool('tricky_questions')
            
            user_prompt = prompt_builder_chain.build()
        # ---------------------------
        
        self._log_processing_start(source_path, output_markdown_file, prompt_type)
        
        try:
            # Process chunks using the provided processor
            for chunk_data, chunk_info in chunk_processor(source_path, user_prompt, paths):
                if not chunk_data:
                    break
                
                self._log_chunk_progress(chunk_info)
                
                try:
                    # Process the chunk and get the final output
                    final_output = self._process_single_chunk(chunk_data, user_prompt, paths)
                    
                    self._log_content_preview(final_output)
                    self.markdown_utils.update_markdown_file(final_output, output_markdown_file)
                    
                    # Handle file limits
                    api_call_counter += 1
                    if api_call_counter >= api_call_limit_per_file:
                        output_file_counter += 1
                        output_markdown_file = self._create_output_file(paths, output_file_counter)
                        api_call_counter = 0
                        logger.info(f"Switching to new output file: {output_markdown_file}")
                
                except Exception as e:
                    logger.error(f"Error processing {chunk_info}: {e}")
                    break
            
            logger.info(f"Completed processing {source_path}")
            
        except Exception as e:
            logger.error(f"Failed to process {source_path}: {e}")

    # ===========================
    # Abstract Methods
    # ===========================
    
    @abstractmethod
    def _process_single_chunk(self, chunk_data: Any, user_prompt: str, paths: Dict[str, str]) -> str:
        """
        Process a single chunk of data. Must be implemented by subclasses.
        
        Args:
            chunk_data: Data for the chunk (format depends on processor type)
            user_prompt: The prompt to use for LLM interaction
            paths: Dictionary containing output path information
            
        Returns:
            str: Processed markdown content
        """
        pass

    @abstractmethod
    def process(self, file_path: str, output_dir: str, prompt_type: str = None, 
                custom_prompt: str = None, conciseness: str = None, **kwargs) -> None:
        """
        Main processing method. Must be implemented by subclasses.
        
        Args:
            file_path: Path to the file to process
            output_dir: Directory for output files
            prompt_type: Type of prompt to use
            custom_prompt: Custom prompt text
            conciseness: Conciseness level ('short_hand', 'balanced', 'deep_dive')
            **kwargs: Additional processor-specific parameters
        """
        pass

