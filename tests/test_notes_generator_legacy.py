"""The legacy CLI note-generation path must fail clearly, not with AttributeError.

``Config.get_api_keys`` and the Gemini writer were removed with the extraction-only rewrite;
``NotesGenerator`` still exists for the CLI, so it has to report that clearly.
"""

import logging
import tempfile
from pathlib import Path

from src.config_utils import Config
from src.notes_generator.main_notes_generator import (
    LLM_GENERATION_REMOVED_MESSAGE,
    NotesGenerator,
)


def test_process_single_file_reports_llm_removed(caplog):
    generator = NotesGenerator(config=Config())
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "slides.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with caplog.at_level(logging.ERROR):
            result = generator._process_single_file(str(pdf), tmp, "PDF")
    assert result is False
    assert LLM_GENERATION_REMOVED_MESSAGE in caplog.text


def test_batch_process_reports_llm_removed(caplog):
    generator = NotesGenerator(config=Config())
    with tempfile.TemporaryDirectory() as tmp, caplog.at_level(logging.ERROR):
        generator.batch_process(tmp, tmp)
    assert LLM_GENERATION_REMOVED_MESSAGE in caplog.text
