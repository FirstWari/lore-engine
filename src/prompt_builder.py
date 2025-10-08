import logging
from typing import List
from prompt_library import PROMPT_LIBRARY

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds complex LLM prompts by composing parts from a prompt library.
    
    Uses the Builder pattern to create flexible, readable prompts by chaining methods.
    Each method adds a specific component to the prompt, and build() assembles the final result.
    
    Example:
        prompt = (PromptBuilder()
                  .with_base_instructions()
                  .with_mode('slides')
                  .with_conciseness('balanced')
                  .with_tool('tables')
                  .with_tool('mermaid_diagrams')
                  .build())
    """
    
    def __init__(self):
        """Initialize the prompt builder with the prompt library."""
        self.library = PROMPT_LIBRARY
        self._prompt_parts: List[str] = []

    def with_base_instructions(self):
        """
        Add the base instructions that apply to all prompt types.
        These include general formatting rules, markdown guidelines, etc.
        
        Returns:
            self: For method chaining
        """
        self._prompt_parts.append(self.library['base']['instructions'])
        return self

    def with_mode(self, mode: str):
        """
        Add mode-specific instructions for different content types.
        
        Args:
            mode: The processing mode ('slides', 'handwritten', 'captions')
            
        Returns:
            self: For method chaining
            
        Raises:
            ValueError: If the mode is not recognized
        """
        if mode in self.library['modes']:
            self._prompt_parts.append(self.library['modes'][mode])
        else:
            available_modes = ', '.join(self.library['modes'].keys())
            raise ValueError(f"Unknown prompt mode: '{mode}'. Available modes: {available_modes}")
        return self

    def with_conciseness(self, level: str):
        """
        Add conciseness level instructions.
        
        Args:
            level: The conciseness level ('default', 'short_hand', 'balanced', 'deep_dive')
            
        Returns:
            self: For method chaining
            
        Raises:
            ValueError: If the conciseness level is not recognized
        """
        if level in self.library['conciseness']:
            # Don't add anything if it's an empty string (like 'default')
            prompt_text = self.library['conciseness'][level]
            if prompt_text:
                self._prompt_parts.append(prompt_text)
        else:
            available_levels = ', '.join(self.library['conciseness'].keys())
            raise ValueError(f"Unknown conciseness level: '{level}'. Available levels: {available_levels}")
        return self

    def with_output_format(self, format: str):
        """
        Add output format instructions.
        
        Args:
            format: The output format ('notes', 'practice_problems', 'formula_sheet')
            
        Returns:
            self: For method chaining
            
        Raises:
            ValueError: If the output format is not recognized
        """
        if format in self.library['output_format']:
            # Don't add anything if it's an empty string (like 'notes')
            prompt_text = self.library['output_format'][format]
            if prompt_text:
                self._prompt_parts.append(prompt_text)
        else:
            available_formats = ', '.join(self.library['output_format'].keys())
            raise ValueError(f"Unknown output format: '{format}'. Available formats: {available_formats}")
        return self

    def with_tool(self, tool_name: str):
        """
        Add instructions for a specific tool or feature.
        
        Args:
            tool_name: The tool to enable ('tables', 'mermaid_diagrams', 'tricky_questions')
            
        Returns:
            self: For method chaining
            
        Raises:
            ValueError: If the tool is not recognized
        """
        if tool_name in self.library['tools']:
            self._prompt_parts.append(self.library['tools'][tool_name])
        else:
            available_tools = ', '.join(self.library['tools'].keys())
            raise ValueError(f"Unknown tool: '{tool_name}'. Available tools: {available_tools}")
        return self
    
    def with_custom_content(self, custom_prompt_content: str):
        """
        Replace all previous instructions with custom content.
        This is useful when users want complete control over the prompt.
        
        Args:
            custom_prompt_content: Custom prompt text to use instead of library content
            
        Returns:
            self: For method chaining
        """
        if custom_prompt_content:
            # Custom content replaces everything
            self._prompt_parts = [custom_prompt_content]
        else:
            # Provide a placeholder if a custom prompt is specified but empty
            self._prompt_parts = [self.library['custom']['placeholder']]
        return self

    def build(self) -> str:
        """
        Assemble all selected parts into a final prompt string.
        
        The parts are joined with double newlines for readability.
        After building, the internal state is reset so the builder can be reused.
        
        Returns:
            str: The complete assembled prompt
        """
        if not self._prompt_parts:
            logger.warning("Building an empty prompt. Did you forget to add components?")
        
        final_prompt = "\n\n".join(self._prompt_parts)
        
        # Reset for the next build
        self._prompt_parts = []
        
        return final_prompt

