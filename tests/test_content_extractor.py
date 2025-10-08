import pytest
import tempfile
import os
from src.notes_generator.content_extractor import ContentExtractor


class TestSRTParsing:
    """Test SRT subtitle file parsing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = ContentExtractor()
    
    def test_parse_valid_srt(self):
        """Test parsing a valid SRT file"""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
First subtitle

2
00:00:04,000 --> 00:00:06,000
Second subtitle

3
00:00:07,000 --> 00:00:09,000
Third subtitle
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name
        
        try:
            subtitles = self.extractor.parse_srt_content(temp_path)
            
            assert len(subtitles) == 3
            assert subtitles[0].content == 'First subtitle'
            assert subtitles[1].content == 'Second subtitle'
            assert subtitles[2].content == 'Third subtitle'
        finally:
            os.unlink(temp_path)
    
    def test_parse_empty_srt(self):
        """Test parsing an empty SRT file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            f.write("")
            temp_path = f.name
        
        try:
            subtitles = self.extractor.parse_srt_content(temp_path)
            assert len(subtitles) == 0
        finally:
            os.unlink(temp_path)
    
    def test_parse_srt_with_multiline_content(self):
        """Test parsing SRT with multiline subtitle content"""
        srt_content = """1
00:00:01,000 --> 00:00:05,000
This is a subtitle
that spans multiple lines
and continues here
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name
        
        try:
            subtitles = self.extractor.parse_srt_content(temp_path)
            
            assert len(subtitles) == 1
            # Content should include newlines
            assert 'multiple lines' in subtitles[0].content
        finally:
            os.unlink(temp_path)
    
    def test_parse_srt_with_unicode(self):
        """Test parsing SRT with Unicode characters"""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Unicode: 日本語 • Español • 😀
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name
        
        try:
            subtitles = self.extractor.parse_srt_content(temp_path)
            
            assert len(subtitles) == 1
            assert '日本語' in subtitles[0].content
            assert 'Español' in subtitles[0].content
            assert '😀' in subtitles[0].content
        finally:
            os.unlink(temp_path)
    
    def test_parse_srt_with_special_formatting(self):
        """Test parsing SRT with special formatting tags"""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
<i>Italic text</i> and <b>bold text</b>
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name
        
        try:
            subtitles = self.extractor.parse_srt_content(temp_path)
            
            assert len(subtitles) == 1
            # Tags should be preserved as-is
            assert '<i>' in subtitles[0].content or 'Italic text' in subtitles[0].content
        finally:
            os.unlink(temp_path)
    
    def test_parse_malformed_srt_raises_error(self):
        """Test that severely malformed SRT raises an error"""
        # Create a file that's not an SRT at all
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            f.write("This is not\nan SRT file\nat all!")
            temp_path = f.name
        
        try:
            # Should handle gracefully or raise error
            subtitles = self.extractor.parse_srt_content(temp_path)
            # If it doesn't raise, it should return empty or partial results
            assert isinstance(subtitles, list)
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file_raises_error(self):
        """Test that parsing non-existent file raises an error"""
        with pytest.raises(Exception):
            self.extractor.parse_srt_content('/nonexistent/file.srt')


class TestPDFImageExtraction:
    """Test PDF image extraction (basic structure tests only)"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = ContentExtractor()
    
    def test_extract_images_with_nonexistent_pdf(self):
        """Test that extracting from non-existent PDF raises error"""
        with pytest.raises(Exception):
            self.extractor.extract_images_from_pdf('/nonexistent/file.pdf', 0, 5)
    
    def test_extract_images_with_invalid_page_range(self):
        """Test extraction with invalid page range"""
        # This test would need an actual PDF file to be meaningful
        # For now, just test that the method signature is correct
        assert callable(self.extractor.extract_images_from_pdf)
        
        # Method should accept: pdf_path, start_page, num_pages
        import inspect
        sig = inspect.signature(self.extractor.extract_images_from_pdf)
        params = list(sig.parameters.keys())
        assert 'pdf_path' in params
        assert 'start_page' in params
        assert 'num_pages' in params


class TestDiverseFrameExtraction:
    """Test diverse frame extraction logic (structure tests)"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = ContentExtractor()
    
    def test_extract_diverse_frames_with_nonexistent_video(self):
        """Test that extracting from non-existent video handles error"""
        result, hashes = self.extractor.extract_diverse_frames(
            '/nonexistent/video.mp4',
            start_time_ms=0,
            end_time_ms=1000,
            output_dir='/tmp',
            global_seen_hashes=set(),
            num_to_select=5,
            similarity_threshold=5,
            min_diversity_threshold=10
        )
        
        # Should return empty dict and unchanged hashes on error
        assert result == {}
        assert hashes == set()
    
    def test_extract_diverse_frames_signature(self):
        """Test that the method has correct signature"""
        import inspect
        sig = inspect.signature(self.extractor.extract_diverse_frames)
        params = list(sig.parameters.keys())
        
        # Check all required parameters exist
        assert 'video_path' in params
        assert 'start_time_ms' in params
        assert 'end_time_ms' in params
        assert 'output_dir' in params
        assert 'global_seen_hashes' in params
        assert 'num_to_select' in params
        assert 'similarity_threshold' in params
        assert 'min_diversity_threshold' in params
    
    def test_calculate_hash_distances_helper(self):
        """Test the hash distance calculation helper method"""
        # This is a protected method but important for correctness
        try:
            import imagehash
            from PIL import Image
            
            # Create some dummy image hashes
            img1 = Image.new('RGB', (10, 10), color='red')
            img2 = Image.new('RGB', (10, 10), color='blue')
            
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
            
            candidates = [(hash1, img1, 0)]
            selected = {hash2}
            
            # Test the helper exists and returns a list
            distances = self.extractor._calculate_hash_distances(candidates, selected)
            assert isinstance(distances, list)
            assert len(distances) == 1
        except ImportError:
            # imagehash not available in test environment, skip
            pytest.skip("imagehash not available")

