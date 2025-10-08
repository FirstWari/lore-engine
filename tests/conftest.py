"""
Pytest configuration and shared fixtures for GeminiNotes tests.

This file contains common fixtures and configuration that can be
shared across all test files.
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file():
    """Provide a temporary file that is cleaned up after the test"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    
    yield temp_path
    
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def sample_srt_content():
    """Provide sample SRT content for testing"""
    return """1
00:00:01,000 --> 00:00:03,000
First subtitle line

2
00:00:04,000 --> 00:00:06,000
Second subtitle line

3
00:00:07,000 --> 00:00:10,000
Third subtitle line
with multiple lines
"""


@pytest.fixture
def sample_config_dict():
    """Provide a sample configuration dictionary"""
    return {
        "model_name": "gemini-2.5-flash",
        "temperature": 0.7,
        "pages_per_chunk": 5,
        "lines_per_chunk": 50,
        "output_prefix": "refined",
        "api_key": ["test_key_1", "test_key_2"]
    }


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing"""
    return "test_api_key_mock_12345"

