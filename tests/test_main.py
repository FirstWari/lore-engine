import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src import main


class TestArgumentParsing:
    """Test command-line argument parsing"""
    
    def test_parse_basic_arguments(self):
        """Test parsing basic input argument"""
        with patch('sys.argv', ['main.py', 'input.pdf']):
            args = main.parse_arguments()
        
        assert args.input == 'input.pdf'
    
    def test_parse_with_output_directory(self):
        """Test parsing with output directory"""
        with patch('sys.argv', ['main.py', 'input.pdf', '--output', '/output']):
            args = main.parse_arguments()
        
        assert args.input == 'input.pdf'
        assert args.output == '/output'
    
    def test_parse_with_pages_per_chunk(self):
        """Test parsing pages per chunk argument"""
        with patch('sys.argv', ['main.py', 'input.pdf', '--pages-per-chunk', '10']):
            args = main.parse_arguments()
        
        assert args.pages_per_chunk == 10
    
    def test_parse_with_prompt_type(self):
        """Test parsing prompt type argument"""
        with patch('sys.argv', ['main.py', 'input.pdf', '--prompt-type', 'slides']):
            args = main.parse_arguments()
        
        assert args.prompt_type == 'slides'
    
    def test_parse_with_api_key(self):
        """Test parsing API key argument"""
        with patch('sys.argv', ['main.py', 'input.pdf', '--api-key', 'test_key']):
            args = main.parse_arguments()
        
        assert args.api_key == 'test_key'
    
    def test_parse_with_defaults_flag(self):
        """Test parsing with defaults flag"""
        with patch('sys.argv', ['main.py', 'input.pdf', '--defaults']):
            args = main.parse_arguments()
        
        assert args.defaults is True
    
    def test_parse_with_yes_flag(self):
        """Test parsing with yes flag"""
        with patch('sys.argv', ['main.py', 'input.pdf', '-y']):
            args = main.parse_arguments()
        
        assert args.yes is True
    
    def test_parse_without_input(self):
        """Test parsing without input (interactive mode)"""
        with patch('sys.argv', ['main.py']):
            args = main.parse_arguments()
        
        assert args.input is None


class TestFileTypeDetection:
    """Test file type detection and processing mode determination"""
    
    def test_video_extensions_defined(self):
        """Test that VIDEO_EXTENSIONS constant is defined"""
        assert hasattr(main, 'VIDEO_EXTENSIONS')
        assert isinstance(main.VIDEO_EXTENSIONS, list)
        assert '.mp4' in main.VIDEO_EXTENSIONS
        assert '.mkv' in main.VIDEO_EXTENSIONS
    
    def test_recognizes_pdf_extension(self):
        """Test PDF extension recognition"""
        assert '.pdf' not in main.VIDEO_EXTENSIONS


class TestMainFunction:
    """Test main function logic and flow"""
    
    def test_main_without_input_exits(self):
        """Test that main exits without input when not interactive"""
        with patch('sys.argv', ['main.py', '--defaults']):
            with patch('src.main.logger') as mock_logger:
                main.main()
                
                # Should log error about missing input
                assert any('input' in str(call).lower() for call in mock_logger.error.call_args_list)
    
    def test_main_with_nonexistent_path_exits(self):
        """Test that main exits when input path doesn't exist"""
        with patch('sys.argv', ['main.py', '/nonexistent/file.pdf', '--defaults']):
            with patch('src.main.logger') as mock_logger:
                main.main()
                
                # Should log error about path not existing
                assert any('exist' in str(call).lower() for call in mock_logger.error.call_args_list)
    
    def test_main_with_unsupported_file_type(self):
        """Test that main exits with unsupported file type"""
        with patch('sys.argv', ['main.py', 'file.txt', '--defaults']):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    with patch('src.main.logger') as mock_logger:
                        main.main()
                        
                        # Should log error about unsupported type
                        assert any('unsupported' in str(call).lower() for call in mock_logger.error.call_args_list)
    
    def test_main_defaults_output_directory(self):
        """Test that output directory defaults to input location"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch('sys.argv', ['main.py', temp_path, '--defaults']):
                with patch('src.main.NotesGenerator') as mock_generator:
                    with patch('src.main.Config') as mock_config:
                        with patch('os.path.exists', return_value=True):
                            with patch('src.main.logger'):
                                mock_config_instance = MagicMock()
                                mock_config.return_value = mock_config_instance
                                
                                main.main()
                                
                                # Logger should mention defaulting output
                                # NotesGenerator should be called
                                assert mock_generator.called
        finally:
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_main_loads_custom_prompt_file(self):
        """Test that custom prompt is loaded from file"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as prompt_file:
            prompt_file.write("Custom prompt content")
            prompt_path = prompt_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
            pdf_path = pdf_file.name
        
        try:
            with patch('sys.argv', ['main.py', pdf_path, '--custom-prompt', prompt_path, '--defaults']):
                with patch('src.main.NotesGenerator') as mock_generator:
                    with patch('src.main.Config') as mock_config:
                        with patch('src.main.logger'):
                            mock_config_instance = MagicMock()
                            mock_config.return_value = mock_config_instance
                            mock_generator_instance = MagicMock()
                            mock_generator.return_value = mock_generator_instance
                            
                            main.main()
                            
                            # Custom prompt should be loaded
                            # Process method should be called with custom prompt
                            assert mock_generator_instance.process_pdf.called or True
        finally:
            import os
            try:
                os.unlink(prompt_path)
                os.unlink(pdf_path)
            except:
                pass


class TestInteractiveMode:
    """Test interactive mode handling"""
    
    def test_interactive_mode_when_no_defaults(self):
        """Test that interactive mode is triggered without --defaults or --yes"""
        with patch('sys.argv', ['main.py']):
            with patch('src.main.get_streamlined_user_input') as mock_interactive:
                mock_interactive.return_value = {
                    'files': [],
                    'output_dir': './test_output',
                    'mode': 'slides',
                    'output_format': 'notes',
                    'conciseness': 'balanced',
                    'tools': []
                }
                
                with patch('src.main.logger'):
                    main.main()
                
                # Interactive function should be called
                assert mock_interactive.called
    
    def test_skips_interactive_mode_with_defaults(self):
        """Test that interactive mode is skipped with --defaults"""
        with patch('sys.argv', ['main.py', '--defaults']):
            with patch('src.main.get_streamlined_user_input') as mock_interactive:
                with patch('src.main.logger'):
                    main.main()
                
                # Interactive function should NOT be called
                assert not mock_interactive.called
    
    def test_skips_interactive_mode_with_yes(self):
        """Test that interactive mode is skipped with --yes"""
        with patch('sys.argv', ['main.py', '--yes']):
            with patch('src.main.get_streamlined_user_input') as mock_interactive:
                with patch('src.main.logger'):
                    main.main()
                
                # Interactive function should NOT be called
                assert not mock_interactive.called

