import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from src.config_utils import Config


class TestConfigLoading:
    """Test configuration file loading and defaults"""
    
    def test_default_config_values(self):
        """Ensure default configuration values are set correctly"""
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config()
        
        assert config.get('model_name') == 'gemini-2.5-flash'
        assert config.get('temperature') == 0.7
        assert config.get('pages_per_chunk') == 5
        assert config.get('lines_per_chunk') == 50
        assert config.get('output_prefix') == 'refined'
    
    def test_load_config_from_valid_json(self):
        """Test loading configuration from a valid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({'pages_per_chunk': 10, 'temperature': 0.5}, f)
            temp_path = f.name
        
        try:
            with patch.object(Config, '_load_api_keys', return_value=[]):
                config = Config(temp_path)
            
            assert config.get('pages_per_chunk') == 10
            assert config.get('temperature') == 0.5
            assert config.get('model_name') == 'gemini-2.5-flash'  # Still has defaults
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_invalid_json(self):
        """Test that invalid JSON falls back to defaults"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with patch.object(Config, '_load_api_keys', return_value=[]):
                config = Config(temp_path)
            
            # Should fallback to defaults
            assert config.get('pages_per_chunk') == 5
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_nonexistent_file(self):
        """Test that non-existent config file uses defaults"""
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config('/nonexistent/config.json')
        
        assert config.get('pages_per_chunk') == 5
        assert config.get('temperature') == 0.7


class TestAPIKeyLoading:
    """Test API key loading from various sources"""
    
    def test_load_numbered_api_keys_from_env(self):
        """Test loading numbered API keys (GEMINI_API_KEY_1, _2, _3, ...)"""
        def mock_getenv(key):
            env_vars = {
                "GEMINI_API_KEY_1": "key1",
                "GEMINI_API_KEY_2": "key2",
                "GEMINI_API_KEY_3": "key3",
            }
            return env_vars.get(key)
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', side_effect=mock_getenv):
                config = Config()
        
        keys = config.get_api_keys()
        assert len(keys) == 3
        assert keys == ["key1", "key2", "key3"]
    
    def test_load_numbered_api_keys_with_whitespace(self):
        """Test that numbered API keys are trimmed"""
        def mock_getenv(key):
            env_vars = {
                "GEMINI_API_KEY_1": " key1 ",
                "GEMINI_API_KEY_2": " key2 ",
            }
            return env_vars.get(key)
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', side_effect=mock_getenv):
                config = Config()
        
        keys = config.get_api_keys()
        assert keys == ["key1", "key2"]
    
    def test_load_single_gemini_api_key(self):
        """Test loading from single GEMINI_API_KEY (fallback)"""
        def mock_getenv(key):
            if key == "GEMINI_API_KEY":
                return "single_key"
            return None
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', side_effect=mock_getenv):
                config = Config()
        
        keys = config.get_api_keys()
        assert len(keys) == 1
        assert keys == ["single_key"]
    
    def test_load_comma_separated_api_keys(self):
        """Test loading comma-separated API keys from GEMINI_API_KEY"""
        def mock_getenv(key):
            if key == "GEMINI_API_KEY":
                return "key1,key2,key3"
            return None
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', side_effect=mock_getenv):
                config = Config()
        
        keys = config.get_api_keys()
        assert len(keys) == 3
        assert keys == ["key1", "key2", "key3"]
    
    def test_load_api_keys_with_whitespace(self):
        """Test that API keys from environment are trimmed"""
        def mock_getenv(key):
            if key == "GEMINI_API_KEY":
                return " key1 , key2 , key3 "
            return None
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', side_effect=mock_getenv):
                config = Config()
        
        keys = config.get_api_keys()
        assert keys == ["key1", "key2", "key3"]
    
    def test_no_api_keys_available(self):
        """Test when no API keys are available from any source"""
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', return_value=None):
                config = Config()
        
        keys = config.get_api_keys()
        assert keys == []
    
    def test_numbered_keys_take_precedence(self):
        """Test that numbered keys (GEMINI_API_KEY_1, _2) take precedence over GEMINI_API_KEY"""
        def mock_getenv(key):
            env_vars = {
                "GEMINI_API_KEY_1": "numbered_key1",
                "GEMINI_API_KEY_2": "numbered_key2",
                "GEMINI_API_KEY": "fallback_key",
            }
            return env_vars.get(key)
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('os.getenv', side_effect=mock_getenv):
                config = Config()
        
        keys = config.get_api_keys()
        assert keys == ["numbered_key1", "numbered_key2"]


class TestConfigUpdate:
    """Test configuration updates from command-line arguments"""
    
    def test_update_from_args(self):
        """Test updating config from argparse namespace"""
        from argparse import Namespace
        
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config()
        
        args = Namespace(
            model='gemini-1.5-pro',
            pages_per_chunk=15,
            lines_per_chunk=100,
            screenshots_per_minute=2.0,
            output_prefix='custom',
            api_key='arg_key1,arg_key2'
        )
        
        config.update_from_args(args)
        
        assert config.get('model_name') == 'gemini-1.5-pro'
        assert config.get('pages_per_chunk') == 15
        assert config.get('lines_per_chunk') == 100
        assert config.get('screenshots_per_minute') == 2.0
        assert config.get('output_prefix') == 'custom'
        assert config.get_api_keys() == ['arg_key1', 'arg_key2']
    
    def test_update_from_args_with_none_values(self):
        """Test that None values don't override config"""
        from argparse import Namespace
        
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config()
        
        original_pages = config.get('pages_per_chunk')
        
        args = Namespace(
            model=None,
            pages_per_chunk=None,
            lines_per_chunk=None,
            screenshots_per_minute=None,
            output_prefix=None,
            api_key=None
        )
        
        config.update_from_args(args)
        
        # Values should remain unchanged
        assert config.get('pages_per_chunk') == original_pages
        assert config.get('model_name') == 'gemini-2.5-flash'


class TestConfigGet:
    """Test configuration get method"""
    
    def test_get_existing_key(self):
        """Test getting an existing configuration key"""
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config()
        
        assert config.get('temperature') == 0.7
    
    def test_get_nonexistent_key_with_default(self):
        """Test getting a non-existent key with default value"""
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config()
        
        assert config.get('nonexistent_key', 'default_value') == 'default_value'
    
    def test_get_nonexistent_key_without_default(self):
        """Test getting a non-existent key without default"""
        with patch.object(Config, '_load_api_keys', return_value=[]):
            config = Config()
        
        assert config.get('nonexistent_key') is None

