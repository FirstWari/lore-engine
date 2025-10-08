import pytest
import tempfile
import os
from unittest.mock import MagicMock
from src.notes_generator.processors.base_processor import BaseNotesProcessor


class MockProcessor(BaseNotesProcessor):
    """Mock implementation of BaseNotesProcessor for testing"""
    
    def _process_single_chunk(self, chunk_data, user_prompt, paths):
        return f"Processed: {chunk_data}"
    
    def process(self, file_path, output_dir, prompt_type=None, custom_prompt=None, conciseness=None, **kwargs):
        pass


class TestPathPreparation:
    """Test output path preparation and sanitization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        config = MagicMock()
        config.get.return_value = "refined"
        
        self.processor = MockProcessor(
            config=config,
            llm_interaction=MagicMock(),
            content_extractor=MagicMock(),
            markdown_utils=MagicMock()
        )
    
    def test_prepare_output_paths_basic(self):
        """Test basic output path preparation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "My Document.pdf")
            
            paths = self.processor._prepare_output_paths(source_path, tmpdir)
            
            assert paths['original_name'] == 'My Document'
            assert paths['fs_safe_name'] == 'My_Document'
            assert paths['fs_safe_prefix'] == 'refined'
            assert paths['display_title'] == 'My Document'
            assert paths['output_dir'] == tmpdir
    
    def test_sanitize_spaces_in_filename(self):
        """Test that spaces are converted to underscores"""
        source_path = "/path/to/file with many spaces.pdf"
        
        paths = self.processor._prepare_output_paths(source_path, "/output")
        
        assert paths['fs_safe_name'] == 'file_with_many_spaces'
        assert ' ' not in paths['fs_safe_name']
    
    def test_sanitize_prefix_with_spaces(self):
        """Test that prefix spaces are also sanitized"""
        config = MagicMock()
        config.get.return_value = "my custom prefix"
        
        processor = MockProcessor(
            config=config,
            llm_interaction=MagicMock(),
            content_extractor=MagicMock(),
            markdown_utils=MagicMock()
        )
        
        paths = processor._prepare_output_paths("/path/to/file.pdf", "/output")
        
        assert paths['fs_safe_prefix'] == 'my_custom_prefix'
        assert ' ' not in paths['fs_safe_prefix']
    
    def test_display_title_formatting(self):
        """Test that display title is properly formatted"""
        source_path = "/path/to/my-lecture_notes-2024.pdf"
        
        paths = self.processor._prepare_output_paths(source_path, "/output")
        
        # Should convert dashes/underscores to spaces and title case
        assert 'My' in paths['display_title']
        assert 'Lecture' in paths['display_title']
        assert 'Notes' in paths['display_title']
        assert '-' not in paths['display_title']
        assert '_' not in paths['display_title']
    
    def test_handle_file_without_extension(self):
        """Test handling files without extension"""
        source_path = "/path/to/document"
        
        paths = self.processor._prepare_output_paths(source_path, "/output")
        
        assert paths['original_name'] == 'document'
        assert paths['fs_safe_name'] == 'document'
    
    def test_output_directory_created(self):
        """Test that output directory is created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_output_dir = os.path.join(tmpdir, "new_dir")
            
            paths = self.processor._prepare_output_paths("/path/to/file.pdf", new_output_dir)
            
            # Directory should be created
            assert os.path.exists(new_output_dir)
            assert paths['output_dir'] == new_output_dir


class TestOutputFileCreation:
    """Test output markdown file creation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        config = MagicMock()
        config.get.return_value = "refined"
        
        self.processor = MockProcessor(
            config=config,
            llm_interaction=MagicMock(),
            content_extractor=MagicMock(),
            markdown_utils=MagicMock()
        )
    
    def test_create_output_file_with_counter(self):
        """Test creating output file with part counter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = {
                'output_dir': tmpdir,
                'fs_safe_prefix': 'refined',
                'fs_safe_name': 'test_doc',
                'display_title': 'Test Doc'
            }
            
            output_file = self.processor._create_output_file(paths, 1)
            
            assert os.path.exists(output_file)
            assert 'refined_test_doc_part1.md' in output_file
            
            # Check file content has header
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert '# Test Doc - Part 1' in content
    
    def test_create_multiple_part_files(self):
        """Test creating multiple part files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = {
                'output_dir': tmpdir,
                'fs_safe_prefix': 'refined',
                'fs_safe_name': 'document',
                'display_title': 'Document'
            }
            
            file1 = self.processor._create_output_file(paths, 1)
            file2 = self.processor._create_output_file(paths, 2)
            file3 = self.processor._create_output_file(paths, 3)
            
            assert os.path.exists(file1)
            assert os.path.exists(file2)
            assert os.path.exists(file3)
            
            assert 'part1' in file1
            assert 'part2' in file2
            assert 'part3' in file3
    
    def test_output_file_has_markdown_extension(self):
        """Test that output files have .md extension"""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = {
                'output_dir': tmpdir,
                'fs_safe_prefix': 'notes',
                'fs_safe_name': 'lecture',
                'display_title': 'Lecture'
            }
            
            output_file = self.processor._create_output_file(paths, 1)
            
            assert output_file.endswith('.md')
    
    def test_output_file_header_includes_part_number(self):
        """Test that file header includes part number"""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = {
                'output_dir': tmpdir,
                'fs_safe_prefix': 'notes',
                'fs_safe_name': 'test',
                'display_title': 'Test Document'
            }
            
            output_file = self.processor._create_output_file(paths, 5)
            
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'Part 5' in content


class TestLoggingHelpers:
    """Test logging helper methods"""
    
    def setup_method(self):
        """Set up test fixtures"""
        config = MagicMock()
        
        self.processor = MockProcessor(
            config=config,
            llm_interaction=MagicMock(),
            content_extractor=MagicMock(),
            markdown_utils=MagicMock()
        )
    
    def test_log_processing_start(self):
        """Test that logging start doesn't raise errors"""
        # These are mainly for coverage and ensuring methods exist
        self.processor._log_processing_start("/path/to/file.pdf", "/output/file.md", "slides")
        # Should not raise
    
    def test_log_chunk_progress(self):
        """Test that logging chunk progress doesn't raise errors"""
        self.processor._log_chunk_progress("chunk 1-5")
        # Should not raise
    
    def test_log_content_preview(self):
        """Test that logging content preview doesn't raise errors"""
        long_content = "x" * 200
        self.processor._log_content_preview(long_content)
        # Should not raise
    
    def test_log_content_preview_with_short_content(self):
        """Test content preview with short content"""
        short_content = "Short content"
        self.processor._log_content_preview(short_content)
        # Should not raise


class TestProcessorInterface:
    """Test processor interface requirements"""
    
    def test_processor_requires_abstract_methods(self):
        """Test that BaseNotesProcessor requires abstract methods"""
        from abc import ABC
        
        assert issubclass(BaseNotesProcessor, ABC)
    
    def test_mock_processor_implements_interface(self):
        """Test that mock processor properly implements interface"""
        config = MagicMock()
        
        processor = MockProcessor(
            config=config,
            llm_interaction=MagicMock(),
            content_extractor=MagicMock(),
            markdown_utils=MagicMock()
        )
        
        # Should have all required methods
        assert hasattr(processor, 'process')
        assert hasattr(processor, '_process_single_chunk')
        assert callable(processor.process)
        assert callable(processor._process_single_chunk)
    
    def test_processor_stores_dependencies(self):
        """Test that processor stores all dependencies"""
        config = MagicMock()
        llm = MagicMock()
        extractor = MagicMock()
        markdown = MagicMock()
        
        processor = MockProcessor(
            config=config,
            llm_interaction=llm,
            content_extractor=extractor,
            markdown_utils=markdown
        )
        
        assert processor.config is config
        assert processor.llm_interaction is llm
        assert processor.content_extractor is extractor
        assert processor.markdown_utils is markdown

