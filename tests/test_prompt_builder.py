import pytest
from src.prompt_builder import PromptBuilder


class TestPromptBuilderBasics:
    """Test basic prompt builder functionality"""
    
    def test_empty_builder_warns_and_returns_empty(self):
        """Test building without adding any components"""
        builder = PromptBuilder()
        result = builder.build()
        assert result == ""
    
    def test_builder_can_be_reused(self):
        """Test that builder can be reused after build()"""
        builder = PromptBuilder()
        
        # First build
        prompt1 = builder.with_base_instructions().build()
        assert len(prompt1) > 0
        
        # Second build should work and be independent
        prompt2 = builder.with_mode('slides').build()
        assert prompt2 != prompt1
    
    def test_method_chaining(self):
        """Test that methods return self for chaining"""
        builder = PromptBuilder()
        result = builder.with_base_instructions()
        assert result is builder


class TestModeSelection:
    """Test mode-specific prompt generation"""
    
    def test_slides_mode(self):
        """Test slides mode prompt"""
        builder = PromptBuilder()
        prompt = builder.with_mode('slides').build()
        
        assert 'slides' in prompt.lower()
        assert len(prompt) > 0
    
    def test_handwritten_mode(self):
        """Test handwritten mode prompt"""
        builder = PromptBuilder()
        prompt = builder.with_mode('handwritten').build()
        
        assert 'handwritten' in prompt.lower()
        assert len(prompt) > 0
    
    def test_captions_mode(self):
        """Test captions mode prompt"""
        builder = PromptBuilder()
        prompt = builder.with_mode('captions').build()
        
        assert 'transcript' in prompt.lower() or 'caption' in prompt.lower()
        assert len(prompt) > 0
    
    def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises ValueError"""
        builder = PromptBuilder()
        
        with pytest.raises(ValueError) as exc_info:
            builder.with_mode('invalid_mode')
        
        assert 'Unknown prompt mode' in str(exc_info.value)
        assert 'invalid_mode' in str(exc_info.value)


class TestConcisenessLevels:
    """Test conciseness level instructions"""
    
    def test_default_conciseness(self):
        """Test default conciseness (empty string)"""
        builder = PromptBuilder()
        prompt = builder.with_conciseness('default').build()
        
        # Default is empty, so prompt should be empty
        assert prompt == ""
    
    def test_short_hand_conciseness(self):
        """Test short_hand conciseness level"""
        builder = PromptBuilder()
        prompt = builder.with_conciseness('short_hand').build()
        
        assert 'concise' in prompt.lower() or 'short' in prompt.lower()
    
    def test_balanced_conciseness(self):
        """Test balanced conciseness level"""
        builder = PromptBuilder()
        prompt = builder.with_conciseness('balanced').build()
        
        assert 'balanced' in prompt.lower()
    
    def test_deep_dive_conciseness(self):
        """Test deep_dive conciseness level"""
        builder = PromptBuilder()
        prompt = builder.with_conciseness('deep_dive').build()
        
        assert 'deep' in prompt.lower() or 'comprehensive' in prompt.lower()
    
    def test_invalid_conciseness_raises_error(self):
        """Test that invalid conciseness level raises ValueError"""
        builder = PromptBuilder()
        
        with pytest.raises(ValueError) as exc_info:
            builder.with_conciseness('invalid_level')
        
        assert 'Unknown conciseness level' in str(exc_info.value)


class TestToolAddition:
    """Test adding formatting tools to prompts"""
    
    def test_add_tables_tool(self):
        """Test adding tables tool"""
        builder = PromptBuilder()
        prompt = builder.with_tool('tables').build()
        
        assert 'table' in prompt.lower()
    
    def test_add_mermaid_tool(self):
        """Test adding mermaid diagrams tool"""
        builder = PromptBuilder()
        prompt = builder.with_tool('mermaid_diagrams').build()
        
        assert 'mermaid' in prompt.lower()
    
    def test_add_tricky_questions_tool(self):
        """Test adding tricky questions tool"""
        builder = PromptBuilder()
        prompt = builder.with_tool('tricky_questions').build()
        
        assert 'question' in prompt.lower()
    
    def test_invalid_tool_raises_error(self):
        """Test that invalid tool raises ValueError"""
        builder = PromptBuilder()
        
        with pytest.raises(ValueError) as exc_info:
            builder.with_tool('invalid_tool')
        
        assert 'Unknown tool' in str(exc_info.value)
    
    def test_multiple_tools(self):
        """Test adding multiple tools"""
        builder = PromptBuilder()
        prompt = (builder
                  .with_tool('tables')
                  .with_tool('mermaid_diagrams')
                  .with_tool('tricky_questions')
                  .build())
        
        assert 'table' in prompt.lower()
        assert 'mermaid' in prompt.lower()
        assert 'question' in prompt.lower()


class TestCompletePromptBuilding:
    """Test building complete prompts with multiple components"""
    
    def test_full_slides_prompt(self):
        """Test building a complete slides prompt"""
        builder = PromptBuilder()
        prompt = (builder
                  .with_base_instructions()
                  .with_mode('slides')
                  .with_conciseness('balanced')
                  .with_tool('tables')
                  .with_tool('mermaid_diagrams')
                  .build())
        
        # Check that all components are present
        assert len(prompt) > 100  # Should be substantial
        assert 'notes' in prompt.lower()  # From base instructions
        assert 'slides' in prompt.lower()  # From mode
        assert 'balanced' in prompt.lower()  # From conciseness
        assert 'table' in prompt.lower()  # From tools
        assert 'mermaid' in prompt.lower()  # From tools
    
    def test_custom_prompt_replaces_all(self):
        """Test that custom prompt replaces all previous content"""
        builder = PromptBuilder()
        custom_text = "This is my custom prompt for special processing"
        
        prompt = (builder
                  .with_base_instructions()
                  .with_mode('slides')
                  .with_custom_content(custom_text)
                  .build())
        
        # Only custom content should be present
        assert prompt == custom_text
        assert 'slides' not in prompt  # Previous content should be gone
    
    def test_empty_custom_prompt_uses_placeholder(self):
        """Test that empty custom prompt uses placeholder"""
        builder = PromptBuilder()
        prompt = builder.with_custom_content("").build()
        
        # Should contain placeholder text
        assert len(prompt) > 0
        assert 'custom' in prompt.lower() or 'prompt' in prompt.lower()
    
    def test_prompt_parts_joined_with_double_newlines(self):
        """Test that prompt parts are separated by double newlines"""
        builder = PromptBuilder()
        prompt = (builder
                  .with_mode('slides')
                  .with_conciseness('balanced')
                  .build())
        
        # Should have double newlines between sections
        assert '\n\n' in prompt

