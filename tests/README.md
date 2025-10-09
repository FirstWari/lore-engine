# LoreEngine Test Suite

This directory contains unit tests for the LoreEngine project.

## Running Tests

### Run all tests

```bash
pytest
```

### Run tests with verbose output

```bash
pytest -v
```

### Run a specific test file

```bash
pytest tests/test_config_utils.py
```

### Run a specific test class

```bash
pytest tests/test_config_utils.py::TestConfigLoading
```

### Run a specific test

```bash
pytest tests/test_config_utils.py::TestConfigLoading::test_default_config_values
```

### Run tests with coverage report

```bash
pytest --cov=. --cov-report=html
```

## Test Organization

### `test_config_utils.py`

Tests for configuration loading, API key management, and command-line argument handling.

- Configuration file loading (JSON)
- API key loading from multiple sources
- Default value handling
- Error handling for malformed configs

### `test_prompt_builder.py`

Tests for the prompt building system using the Builder pattern.

- Mode selection (slides, handwritten, captions)
- Conciseness levels
- Tool additions (tables, mermaid, etc.)
- Custom prompt handling
- Method chaining

### `test_markdown_utils.py`

Tests for markdown processing and formatting.

- Cleaning and formatting markdown
- Mermaid diagram fixes
- Screenshot placeholder replacement
- File updating and UTF-8 handling

### `test_content_extractor.py`

Tests for content extraction from various sources.

- SRT subtitle parsing
- PDF image extraction interface
- Diverse frame extraction interface
- Unicode and special character handling

### `test_base_processor.py`

Tests for the base processor class functionality.

- Path sanitization and preparation
- Output file creation
- Filesystem-safe naming
- Part numbering for split files

### `test_main.py`

Tests for the main entry point and command-line interface.

- Argument parsing
- File type detection
- Processing mode determination
- Interactive mode handling

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `temp_dir`: Temporary directory for file operations
- `temp_file`: Temporary file that's cleaned up
- `sample_srt_content`: Sample SRT subtitle content
- `sample_config_dict`: Sample configuration dictionary
- `mock_api_key`: Mock API key for testing

## Writing New Tests

When adding new tests:

1. Create a new file named `test_<module_name>.py`
2. Organize tests into classes by functionality
3. Use descriptive test names that explain what's being tested
4. Include docstrings explaining the test purpose
5. Use fixtures from `conftest.py` when appropriate
6. Mock external dependencies (API calls, file system where practical)

## Test Philosophy

These tests focus on:

- **Important functionality**: Configuration, prompt building, path handling
- **Flaky components**: File I/O, text processing, path operations
- **Basic coverage**: Not exhaustive, but covers critical paths
- **Independence**: Tests don't make actual API calls or require external services
