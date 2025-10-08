"""
Streamlined user input module for The Lore Engine.
Config-driven, easily extensible, minimal questions.
"""

import os
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION DEFINITIONS
# ============================================================================

MODES = {
    1: {
        'id': 'slides',
        'label': 'Slides/Presentation (default)',
        'file_extensions': ['.pdf'],
        'is_default': True
    },
    2: {
        'id': 'textbook_chapter',
        'label': 'Textbook chapter',
        'file_extensions': ['.pdf']
    },
    3: {
        'id': 'research_paper',
        'label': 'Research paper',
        'file_extensions': ['.pdf']
    },
    4: {
        'id': 'captions',
        'label': 'Captions (video lectures with/without video)',
        'file_extensions': ['.srt', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
    },
    5: {
        'id': 'handwritten',
        'label': 'Handwritten notes (images)',
        'file_extensions': ['.jpg', '.jpeg', '.png']
    }
}

OUTPUT_FORMATS = {
    1: {
        'id': 'notes',
        'label': 'Notes (default)',
        'is_default': True
    },
    2: {
        'id': 'practice_problems',
        'label': 'Practice problems'
    },
    3: {
        'id': 'formula_sheet',
        'label': 'Formula/Revision sheet (concise pre-exam material)',
        'force_conciseness': 'short_hand'  # Auto-set conciseness
    }
}

CONCISENESS_LEVELS = {
    0: {
        'id': 'default',
        'label': 'Default (hidden - not shown to user)',
        'hidden': True  # Not shown in interactive mode
    },
    1: {
        'id': 'balanced',
        'label': 'Balanced (default)',
        'is_default': True
    },
    2: {
        'id': 'short_hand',
        'label': 'Short-hand (concise)'
    },
    3: {
        'id': 'deep_dive',
        'label': 'Deep-dive (comprehensive)'
    }
}

# Tool enablement rules
TOOL_RULES = {
    'tables': {
        'always': True  # Always enabled
    },
    'mermaid_diagrams': {
        'output_formats': ['notes'],  # Only for notes
    },
    'screenshots': {
        'always': True  # Always enabled
    },
    'tricky_questions': {
        'conciseness': ['balanced', 'deep_dive'],
        'output_formats': ['notes']
    },
    'latex_support': {
        'modes': ['research_paper', 'textbook_chapter']
    }
}

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Ensure user config IDs match prompt library keys"""
    try:
        from prompt_library import PROMPT_LIBRARY
        
        # Check modes
        mode_ids = {opt['id'] for opt in MODES.values()}
        library_modes = set(PROMPT_LIBRARY['modes'].keys())
        
        if mode_ids != library_modes:
            missing = library_modes - mode_ids
            extra = mode_ids - library_modes
            raise ValueError(
                f"Mode config mismatch!\n"
                f"  Missing in user config: {missing}\n"
                f"  Extra in user config: {extra}"
            )
        
        # Check output formats
        format_ids = {opt['id'] for opt in OUTPUT_FORMATS.values()}
        library_formats = set(PROMPT_LIBRARY['output_format'].keys())
        
        if format_ids != library_formats:
            missing = library_formats - format_ids
            extra = format_ids - library_formats
            raise ValueError(
                f"Output format config mismatch!\n"
                f"  Missing in user config: {missing}\n"
                f"  Extra in user config: {extra}"
            )
        
        # Check conciseness
        conciseness_ids = {opt['id'] for opt in CONCISENESS_LEVELS.values()}
        library_conciseness = set(PROMPT_LIBRARY['conciseness'].keys())
        
        if conciseness_ids != library_conciseness:
            missing = library_conciseness - conciseness_ids
            extra = conciseness_ids - library_conciseness
            raise ValueError(
                f"Conciseness config mismatch!\n"
                f"  Missing in user config: {missing}\n"
                f"  Extra in user config: {extra}"
            )
        
        # Check tools (rules don't need to cover all, but mentioned ones must exist)
        tool_ids = set(TOOL_RULES.keys())
        library_tools = set(PROMPT_LIBRARY['tools'].keys())
        
        extra = tool_ids - library_tools
        if extra:
            raise ValueError(f"Tool config references non-existent tools: {extra}")
        
        print("[OK] Configuration validation passed")
        
    except ImportError:
        # prompt_library not available yet - skip validation
        pass

# Run validation on import
validate_config()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ask_choice(question, options_dict, allow_enter=True):
    """
    Generic function to ask a numbered choice question.
    
    Args:
        question: The question to display
        options_dict: Dict with {number: {'id': ..., 'label': ...}}
        allow_enter: Whether pressing Enter selects the default
        
    Returns:
        The 'id' value of the selected option
    """
    print(f"\n{question}")
    
    default_num = None
    for num, opt in sorted(options_dict.items()):
        # Skip hidden options
        if opt.get('hidden'):
            continue
        marker = " ⏎" if opt.get('is_default') else ""
        print(f"[{num}] {opt['label']}{marker}")
        if opt.get('is_default'):
            default_num = num
    
    while True:
        choice = input("→ ").strip()
        
        # Allow Enter for default
        if not choice and allow_enter and default_num:
            return options_dict[default_num]['id']
        
        # Validate input
        try:
            num = int(choice)
            if num in options_dict:
                return options_dict[num]['id']
            else:
                print(f"❌ Invalid choice. Enter a number between 1 and {len(options_dict)}")
        except ValueError:
            print(f"❌ Please enter a number")


def get_files_by_extension(input_path, extensions):
    """Get all files matching the given extensions"""
    if os.path.isfile(input_path):
        # Single file - check if it matches
        if any(input_path.lower().endswith(ext) for ext in extensions):
            return [input_path]
        else:
            return []
    
    # Directory - recursively find matching files
    all_files = []
    for root, dirs, files in os.walk(input_path):
        # Skip screenshot directories
        if 'notes_screenshots' in root:
            continue
        
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                all_files.append(os.path.join(root, file))
    
    return all_files


def get_enabled_tools(mode, conciseness, output_format):
    """Determine which tools to enable based on configuration"""
    enabled = []
    
    for tool_name, rules in TOOL_RULES.items():
        # Check if always enabled
        if rules.get('always'):
            enabled.append(tool_name)
            continue
        
        # Check mode restriction
        if 'modes' in rules and mode not in rules['modes']:
            continue
        
        # Check conciseness restriction
        if 'conciseness' in rules and conciseness not in rules['conciseness']:
            continue
        
        # Check output format restriction
        if 'output_formats' in rules and output_format not in rules['output_formats']:
            continue
        
        # All checks passed
        enabled.append(tool_name)
    
    return enabled

# ============================================================================
# MAIN INTERACTIVE FUNCTION
# ============================================================================

def get_streamlined_user_input():
    """
    Streamlined interactive input - 4-5 questions max with smart defaults.
        
    Returns:
        Dictionary with:
        - files: List of files to process
        - output_dir: Output directory
        - mode: Mode ID (slides, captions, etc.)
        - output_format: Output format ID (notes, practice_problems, etc.)
        - conciseness: Conciseness ID (balanced, short_hand, etc.)
        - tools: List of tool IDs to enable
    """
    
    print("\n" + "="*70)
    print("The Lore Engine - Extract Knowledge From Any Source")
    print("="*70)
    
    # Q1: Input path
    input_path = input("\n1. Input file or folder: ").strip().strip('"')
    if not os.path.exists(input_path):
        print("❌ Path not found!")
        sys.exit(1)
    
    # Store the original input path
    original_input = input_path
    
    # Q2: Output folder (default: next to input)
    input_path_obj = Path(input_path)
    if input_path_obj.is_file():
        # For files, output next to the file
        default_output = str(input_path_obj.parent / f"{input_path_obj.stem}_output")
    else:
        # For directories, output inside the directory
        default_output = str(input_path_obj / f"{input_path_obj.name}_output")
    
    output = input(f"\n2. Output folder? [{default_output}]: ").strip()
    output_dir = output if output else default_output
    
    # Q3: Mode (combined input type + processing mode)
    mode_id = ask_choice("3. What type of content?", MODES)
    
    # Get file extensions and find files
    mode_config = next(opt for opt in MODES.values() if opt['id'] == mode_id)
    file_extensions = mode_config['file_extensions']
    files = get_files_by_extension(input_path, file_extensions)
    
    if not files:
        print(f"\n❌ No files found with extensions: {file_extensions}")
        sys.exit(1)
    
    # Q4: Output format
    output_format_id = ask_choice(
        "4. What do you want to generate?",
        OUTPUT_FORMATS
    )
    
    # Q5: Conciseness (auto-skip if formula sheet)
    output_format_config = next(
        opt for opt in OUTPUT_FORMATS.values()
        if opt['id'] == output_format_id
    )
    
    if 'force_conciseness' in output_format_config:
        # Auto-set for formula sheet
        conciseness_id = output_format_config['force_conciseness']
        print(f"\n5. Detail level: {conciseness_id} (auto-selected for formula sheet)")
    else:
        # Ask normally
        conciseness_id = ask_choice(
            "5. Detail level?",
            CONCISENESS_LEVELS
        )
    
    # Determine tools automatically
    tools = get_enabled_tools(mode_id, conciseness_id, output_format_id)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"[OK] Found {len(files)} file(s) to process")
    print(f"[OK] Mode: {mode_id}")
    print(f"[OK] Output format: {output_format_id}")
    print(f"[OK] Conciseness: {conciseness_id}")
    print(f"[OK] Tools enabled: {', '.join(tools)}")
    print(f"[OK] Output: {output_dir}/Refined_<filename>.md")
    print(f"{'='*70}\n")
    
    return {
        'files': files,
        'output_dir': output_dir,
        'input_path': original_input,  # The original input (file or folder)
        'mode': mode_id,
        'output_format': output_format_id,
        'conciseness': conciseness_id,
        'tools': tools
    }


# ============================================================================
# CLI ARGUMENT PARSING
# ============================================================================

def parse_streamlined_args():
    """Parse command line arguments for streamlined mode"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="The Lore Engine - Extract Knowledge From Any Source",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional
    parser.add_argument("input", nargs='?', help="Input file or folder")
    
    # Options
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--mode",
        choices=[opt['id'] for opt in MODES.values()],
        help="Content type")
    parser.add_argument("--output-format",
        choices=[opt['id'] for opt in OUTPUT_FORMATS.values()],
        help="Output format")
    parser.add_argument("--conciseness",
        choices=[opt['id'] for opt in CONCISENESS_LEVELS.values()],
        help="Detail level")
    
    return parser.parse_args()


def get_user_input_from_args_or_interactive(args=None):
    """
    Get user input either from CLI args or interactively.
    
    Args:
        args: Parsed arguments (optional)
        
    Returns:
        Same dict as get_streamlined_user_input()
    """
    if args is None:
        args = parse_streamlined_args()
    
    # Check if we have enough info to skip interactive
    if args.input and args.mode and args.output_format:
        # CLI mode - use provided args
        input_path = args.input
        if not os.path.exists(input_path):
            print(f"❌ Path not found: {input_path}")
            sys.exit(1)
        
        mode_id = args.mode
        output_format_id = args.output_format
        
        # Output dir
        if args.output:
            output_dir = args.output
        else:
            output_dir = f"./{Path(input_path).stem}_output"
        
        # Conciseness
        output_format_config = next(
            opt for opt in OUTPUT_FORMATS.values()
            if opt['id'] == output_format_id
        )
        
        if 'force_conciseness' in output_format_config:
            conciseness_id = output_format_config['force_conciseness']
        elif args.conciseness:
            conciseness_id = args.conciseness
        else:
            conciseness_id = 'balanced'  # Default
        
        # Get files
        mode_config = next(opt for opt in MODES.values() if opt['id'] == mode_id)
        file_extensions = mode_config['file_extensions']
        files = get_files_by_extension(input_path, file_extensions)
        
        if not files:
            print(f"❌ No files found with extensions: {file_extensions}")
            sys.exit(1)
        
        # Get tools
        tools = get_enabled_tools(mode_id, conciseness_id, output_format_id)
        
        print(f"[OK] Processing {len(files)} file(s) in CLI mode")
        
        return {
            'files': files,
            'output_dir': output_dir,
            'mode': mode_id,
            'output_format': output_format_id,
            'conciseness': conciseness_id,
            'tools': tools
        }
    else:
        # Interactive mode
        return get_streamlined_user_input()


if __name__ == "__main__":
    # Test the config
    result = get_streamlined_user_input()
    print("\nResult:")
    print(result)

