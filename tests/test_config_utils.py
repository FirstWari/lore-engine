import pytest
import json
import os
import tempfile
from pathlib import Path
from src.config_utils import Config

class TestConfigLoading:
    """Test configuration file loading and defaults"""
    
    def test_default_config_values(self):
        """Ensure default configuration values are set correctly"""
        config = Config()
        
        assert config.get('pages_per_chunk') == 10
        assert config.get('lines_per_chunk') == 120
        assert config.get('screenshots_per_minute') == 1.0
        assert config.get('hash_similarity_threshold') == 5
        assert config.get('min_diversity_threshold') == 10
        assert config.get('output_prefix') == 'refined'
    
    def test_load_config_from_valid_json(self):
        """Test loading configuration from a valid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({'pages_per_chunk': 20, 'output_prefix': 'custom'}, f)
            temp_path = f.name
        
        try:
            config = Config(temp_path)
            assert config.get('pages_per_chunk') == 20
            assert config.get('output_prefix') == 'custom'
            assert config.get('lines_per_chunk') == 120  # Still has default
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_invalid_json(self):
        """Test that invalid JSON falls back to defaults"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            config = Config(temp_path)
            assert config.get('pages_per_chunk') == 10
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_nonexistent_file(self):
        """Test that non-existent config file uses defaults"""
        config = Config('/nonexistent/config.json')
        assert config.get('pages_per_chunk') == 10

class TestConfigGet:
    """Test get method with and without defaults"""
    
    def test_get_existing_key(self):
        config = Config()
        assert config.get('pages_per_chunk') == 10
    
    def test_get_nonexistent_key_with_default(self):
        config = Config()
        assert config.get('nonexistent_key', 'default_val') == 'default_val'
    
    def test_get_nonexistent_key_without_default(self):
        config = Config()
        assert config.get('nonexistent_key') is None
