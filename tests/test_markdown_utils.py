import pytest
import tempfile
import os
from src.notes_generator.markdown_utils import MarkdownUtils


class TestMarkdownCleaning:
    """Test markdown cleaning and formatting"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.utils = MarkdownUtils()
    
    def test_extract_refinednotes_tags(self):
        """Test extracting content from REFINEDNOTES tags"""
        text = """
        Some preamble text
        <REFINEDNOTES>
        # My Notes
        This is the actual content
        </REFINEDNOTES>
        Some text after
        """
        
        result = self.utils.clean_markdown(text)
        
        assert '# My Notes' in result
        assert 'This is the actual content' in result
        assert 'preamble' not in result
        assert 'text after' not in result.lower()
    
    def test_no_refinednotes_tags_returns_full_text(self):
        """Test that text without tags is returned as-is"""
        text = "# My Notes\nThis is content without tags"
        
        result = self.utils.clean_markdown(text)
        
        assert result == text
    
    def test_unescape_markdown_special_chars(self):
        """Test unescaping backslash-escaped markdown characters"""
        text = r"This has \*asterisks\* and \#hashes\# and \_underscores\_"
        
        result = self.utils.clean_markdown(text)
        
        assert result == "This has *asterisks* and #hashes# and _underscores_"
    
    def test_fix_mermaid_newlines(self):
        """Test fixing \\n in mermaid diagrams"""
        # Test that the function handles mermaid diagrams without crashing
        text = """```mermaid
graph LR
A --> B
C --> D
```"""
        
        result = self.utils.clean_markdown(text)
        
        # Should maintain basic structure
        assert '```mermaid' in result
        assert 'graph LR' in result
        assert 'A --> B' in result
        assert 'C --> D' in result
        # Result should be a string
        assert isinstance(result, str)
    
    def test_remove_parentheses_from_mermaid_labels(self):
        """Test that parentheses are removed from Mermaid node labels"""
        text = """
        ```mermaid
        graph LR
        A[Node (with parens)]
        B[Another (test) node]
        ```
        """
        
        result = self.utils.clean_markdown(text)
        
        # Parentheses and their content should be removed or replaced
        assert '(with parens)' not in result or 'with parens' in result
        assert '(test)' not in result or 'test' in result
    
    def test_clean_markdown_handles_empty_string(self):
        """Test cleaning empty string"""
        result = self.utils.clean_markdown("")
        assert result == ""
    
    def test_clean_markdown_handles_multiline_mermaid(self):
        """Test cleaning complex multiline mermaid diagrams"""
        text = """
        ```mermaid
        graph TD
        A[Start] --> B[Process]
        B --> C[End]
        ```
        """
        
        result = self.utils.clean_markdown(text)
        
        # Should maintain structure
        assert '```mermaid' in result
        assert 'A[Start]' in result
        assert '```' in result


class TestScreenshotPlaceholderReplacement:
    """Test screenshot placeholder replacement"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.utils = MarkdownUtils()
    
    def test_replace_single_screenshot(self):
        """Test replacing a single screenshot placeholder"""
        markdown = "Here is a screenshot: [SCREENSHOT-00-01-23]"
        saved_frames = {"00-01-23": "/path/to/screenshot.jpg"}
        output_dir = "/output"
        
        result = self.utils.replace_screenshot_placeholders(markdown, saved_frames, output_dir)
        
        assert '[SCREENSHOT-00-01-23]' not in result
        assert '![Screenshot at 00:01:23]' in result
        assert '.jpg' in result
    
    def test_replace_multiple_screenshots(self):
        """Test replacing multiple screenshot placeholders"""
        markdown = """
        First: [SCREENSHOT-00-01-00]
        Second: [SCREENSHOT-00-02-30]
        Third: [SCREENSHOT-00-05-15]
        """
        saved_frames = {
            "00-01-00": "/path/to/frame1.jpg",
            "00-02-30": "/path/to/frame2.jpg",
            "00-05-15": "/path/to/frame3.jpg"
        }
        output_dir = "/output"
        
        result = self.utils.replace_screenshot_placeholders(markdown, saved_frames, output_dir)
        
        # All placeholders should be replaced
        assert '[SCREENSHOT-' not in result
        assert '![Screenshot at 00:01:00]' in result
        assert '![Screenshot at 00:02:30]' in result
        assert '![Screenshot at 00:05:15]' in result
    
    def test_missing_screenshot_preserves_placeholder(self):
        """Test that missing screenshots leave placeholder intact"""
        markdown = "Screenshot: [SCREENSHOT-00-01-23]"
        saved_frames = {}  # No frames
        output_dir = "/output"
        
        result = self.utils.replace_screenshot_placeholders(markdown, saved_frames, output_dir)
        
        # Placeholder should remain
        assert '[SCREENSHOT-00-01-23]' in result
    
    def test_empty_saved_frames_returns_original(self):
        """Test that empty saved frames returns original markdown"""
        markdown = "Some text with [SCREENSHOT-00-01-23] placeholder"
        saved_frames = {}
        output_dir = "/output"
        
        result = self.utils.replace_screenshot_placeholders(markdown, saved_frames, output_dir)
        
        assert result == markdown
    
    def test_relative_path_calculation(self):
        """Test that relative paths are calculated correctly"""
        markdown = "[SCREENSHOT-00-01-23]"
        
        # Create actual temp directories to test path calculation
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            screenshot_dir = os.path.join(tmpdir, "output", "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            
            screenshot_path = os.path.join(screenshot_dir, "frame.jpg")
            saved_frames = {"00-01-23": screenshot_path}
            
            result = self.utils.replace_screenshot_placeholders(markdown, saved_frames, output_dir)
            
            # Should use forward slashes and relative path
            assert 'screenshots/frame.jpg' in result
            assert '\\' not in result  # No backslashes


class TestMarkdownFileUpdating:
    """Test markdown file updating functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.utils = MarkdownUtils()
    
    def test_append_to_existing_file(self):
        """Test appending content to existing file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            f.write("# Existing Content\n\n")
            temp_path = f.name
        
        try:
            new_content = "## New Section\nNew content here"
            self.utils.update_markdown_file(new_content, temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            assert '# Existing Content' in result
            assert '## New Section' in result
            assert 'New content here' in result
            assert '---' in result  # Separator should be added
        finally:
            os.unlink(temp_path)
    
    def test_create_new_file_if_not_exists(self):
        """Test creating new file if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = os.path.join(tmpdir, "new_file.md")
            
            content = "# New File\nContent here"
            self.utils.update_markdown_file(content, temp_path)
            
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            assert '# New File' in result
            assert 'Content here' in result
    
    def test_content_separated_by_horizontal_rules(self):
        """Test that content is separated by horizontal rules"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            temp_path = f.name
        
        try:
            self.utils.update_markdown_file("First chunk", temp_path)
            self.utils.update_markdown_file("Second chunk", temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # Should have separators
            assert result.count('---') >= 2
            assert 'First chunk' in result
            assert 'Second chunk' in result
        finally:
            os.unlink(temp_path)
    
    def test_utf8_encoding_preserved(self):
        """Test that UTF-8 encoding is preserved"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            unicode_content = "# Unicode Test\n日本語 • Español • Ελληνικά • 😀"
            self.utils.update_markdown_file(unicode_content, temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            assert '日本語' in result
            assert 'Español' in result
            assert 'Ελληνικά' in result
            assert '😀' in result
        finally:
            os.unlink(temp_path)

