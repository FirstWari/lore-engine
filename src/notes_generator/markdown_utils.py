import re
import logging
import os

logger = logging.getLogger(__name__)

class MarkdownUtils:
    def __init__(self):
        pass

    def _fix_unclosed_code_blocks(self, text: str) -> str:
        """
        Detects and fixes unclosed code blocks that would break subsequent chunk rendering.
        
        An unclosed code fence (```) causes all following content to be interpreted as code,
        breaking markdown rendering. This is critical for chunked LLM processing.
        
        Returns:
            Text with balanced code fences (closes any unclosed blocks)
        """
        # Count opening code fences (```)
        # Match any line that starts with ``` (possibly with language identifier)
        opening_fences = re.findall(r'^```\w*', text, re.MULTILINE)
        
        # Count closing code fences (standalone ``` on a line)
        closing_fences = re.findall(r'^```\s*$', text, re.MULTILINE)
        
        num_opening = len(opening_fences)
        num_closing = len(closing_fences)
        
        # If unbalanced, we have unclosed code blocks
        if num_opening > num_closing:
            num_unclosed = num_opening - num_closing
            logger.warning(f"Detected {num_unclosed} unclosed code block(s). Auto-closing to prevent rendering issues.")
            
            # Append closing fences to fix the issue
            # Add them at the end with newlines for proper formatting
            text = text.rstrip() + '\n' + ('```\n' * num_unclosed)
            
        elif num_opening < num_closing:
            # This shouldn't happen in normal cases, but log it
            logger.warning(f"Detected extra closing code fences ({num_closing} closings vs {num_opening} openings). This may indicate a parsing issue.")
        
        return text

    def clean_markdown(self, text: str) -> str:
        """Cleans up common Markdown issues, fixes list indentation, and replaces invalid parentheses in mermaid diagrams."""
        
        # --- Extract notes from REFINEDNOTES tags ---
        notes_match = re.search(r'<REFINEDNOTES>(.*?)</REFINEDNOTES>', text, re.DOTALL)
        if notes_match:
            text = notes_match.group(1).strip()
            logger.debug("Extracted notes from <REFINEDNOTES> tags")
        else:
            logger.debug("No <REFINEDNOTES> tags found, using full response")
        
        # --- Fix unclosed code blocks (CRITICAL for chunked processing) ---
        text = self._fix_unclosed_code_blocks(text)
        
        # --- Collapse excessive whitespace (model sometimes generates whitespace loops) ---
        # Replace 3+ consecutive newlines with exactly 2 newlines (one blank line)
        text = re.sub(r'\n\n\n+', '\n\n', text)
        logger.debug("Collapsed excessive blank lines")
        
        # --- Start: Mermaid Parentheses Cleaning ---
        def fix_mermaid_diagram(match):
            """
            Replace parentheses with dashes in Mermaid labels and subgraph names to prevent syntax errors.
            Mermaid does not support parentheses in these contexts, even with quotes.
            
            Preserves the content inside parentheses for readability.
            
            Transforms: 
            - A[Label (with parens)] --> A[Label - with parens]
            - subgraph Name (with parens) --> subgraph Name - with parens
            """
            mermaid_code = match.group(1)
            
            # Replace parentheses with dashes, preserving the content
            # (text) --> - text
            # Handle nested cases and spacing
            def replace_parens(text):
                """Replace (content) with - content, handling spacing nicely"""
                # Replace opening parenthesis with dash
                text = re.sub(r'\s*\(\s*', ' - ', text)
                # Remove closing parenthesis
                text = re.sub(r'\s*\)', '', text)
                # Clean up any double spaces or dashes
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'-\s*-', '-', text)
                return text.strip()
            
            # 1. Fix subgraph names with parentheses
            def fix_subgraph(subgraph_match):
                keyword = subgraph_match.group(1)  # 'subgraph'
                name = subgraph_match.group(2)     # 'Name (with parens)'
                
                if '(' in name or ')' in name:
                    cleaned_name = replace_parens(name)
                    logger.debug(f"Cleaned Mermaid subgraph: '{name}' -> '{cleaned_name}'")
                    return f"{keyword} {cleaned_name}"
                else:
                    return subgraph_match.group(0)
            
            # Match subgraph declarations: subgraph Name Here
            mermaid_code = re.sub(
                r'(subgraph)\s+([^\n\r]+)',
                fix_subgraph,
                mermaid_code
            )
            
            # 2. Fix node labels with parentheses: A[Label (text)]
            def fix_label(label_match):
                node_id = label_match.group(1)      # e.g., F
                label_text = label_match.group(2)   # e.g., MLflow Run (Auto-logging)
                
                if '(' in label_text or ')' in label_text:
                    cleaned_text = replace_parens(label_text)
                    logger.debug(f"Cleaned Mermaid label: '{label_text}' -> '{cleaned_text}'")
                    return f"{node_id}[{cleaned_text}]"
                else:
                    return label_match.group(0)
            
            # Match node labels: NodeID[Label text here]
            mermaid_code = re.sub(
                r'(\w+)\[([^\]]+)\]',
                fix_label,
                mermaid_code
            )
            
            # 3. Fix edge labels that look like ordered lists
            # Mermaid interprets "1. Text" as a markdown list, causing "Unsupported markdown: list" error
            # We need to escape or modify these patterns in edge labels
            def fix_edge_label(edge_match):
                """Fix numbered list-like patterns in edge labels"""
                full_match = edge_match.group(0)
                label = edge_match.group(1) if edge_match.lastindex >= 1 else ""
                
                # Check if label starts with number pattern like "1.", "2a.", "3b.", etc.
                if re.match(r'^\d+[a-z]?\.\s', label):
                    # Replace the period with a colon or dash to avoid list interpretation
                    # "1. Text" -> "1: Text" or "2a. Text" -> "2a: Text"
                    fixed_label = re.sub(r'^(\d+[a-z]?)\.\s', r'\1: ', label)
                    # Reconstruct the edge with the fixed label
                    return full_match.replace(label, fixed_label)
                
                return full_match
            
            # Match edge labels in both pipe and quote formats:
            # -->|label| or --|"label"|--> or -->|"label"|
            mermaid_code = re.sub(
                r'(?:-->|--)\s*[|"]([^|"]+)[|"]',
                fix_edge_label,
                mermaid_code
            )
            
            return f"```mermaid\n{mermaid_code}\n```"
        
        try:
            text = re.sub(r'```mermaid\n(.*?)\n```', fix_mermaid_diagram, text, flags=re.DOTALL)
        except Exception as e:
            logger.warning(f"Error during Mermaid parentheses cleaning: {e}. Skipping cleaning.")
        
        # --- End: Mermaid Parentheses Cleaning ---

        # Fix \n in mermaid diagrams
        def replace_newlines_in_mermaid(match):
            code = match.group(1)
            fixed = code.replace(r'\\n', '\n').replace(r'\n', '\n')
            return f"```mermaid\n{fixed.strip()}\n```"

        text = re.sub(r'```mermaid\n(.*?)\n```', replace_newlines_in_mermaid, text, flags=re.DOTALL)

        # Unescape markdown special chars
        text = re.sub(r'\\([*#_~`\[\]])', r'\1', text)

        return text

    def replace_screenshot_placeholders(self, markdown_text: str, saved_frames: dict, output_dir: str) -> str:
        """
        Replaces image placeholders with markdown image links.
        
        Handles two formats:
        - [SCREENSHOT-HH-MM-SS]: For video frames (timestamp-based)
        - [PAGE-N]: For PDF pages (page number-based)
        
        It calculates the relative path from the markdown file's directory to the image.
        """
        if not saved_frames:
            return markdown_text

        def screenshot_replacer(match):
            timestamp = match.group(1)  # e.g., "00-01-23"

            if timestamp in saved_frames:
                screenshot_file_path = saved_frames[timestamp]
                
                # Calculate the path relative to the markdown file's location (output_dir)
                relative_path = os.path.relpath(screenshot_file_path, output_dir).replace("\\", "/")

                # Create the markdown image tag
                return f"![Screenshot at {timestamp.replace('-', ':')}]({relative_path})"
            else:
                logger.warning(f"Found a placeholder for a non-existent screenshot: [SCREENSHOT-{timestamp}]")
                return match.group(0)  # Return the original placeholder if no match found

        def page_replacer(match):
            page_num = match.group(1)  # e.g., "1", "2", "15"

            if page_num in saved_frames:
                page_file_path = saved_frames[page_num]
                
                # Calculate the path relative to the markdown file's location (output_dir)
                relative_path = os.path.relpath(page_file_path, output_dir).replace("\\", "/")

                # Create the markdown image tag
                return f"![Page {page_num}]({relative_path})"
            else:
                logger.warning(f"Found a placeholder for a non-existent page: [PAGE-{page_num}]")
                return match.group(0)  # Return the original placeholder if no match found

        # Replace video screenshot placeholders: [SCREENSHOT-HH-MM-SS]
        processed_text = re.sub(r'\[SCREENSHOT-([\d-]{8})\]', screenshot_replacer, markdown_text)
        
        # Replace PDF page placeholders: [PAGE-N]
        processed_text = re.sub(r'\[PAGE-(\d+)\]', page_replacer, processed_text)
        
        return processed_text

    def update_markdown_file(self, markdown_text: str, output_file: str) -> None:
        """Updates the Markdown file by appending new content."""
        try:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(markdown_text + "\n\n---\n\n")
            logger.info(f"Updated {output_file} with new content")
        except Exception as e:
            logger.error(f"Error updating markdown file: {e}")
            raise