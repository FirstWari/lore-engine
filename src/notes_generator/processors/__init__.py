"""
Processors module for handling different types of content (PDFs, transcripts).
"""
# sys.path manipulation removed - use proper Python package imports

from notes_generator.processors.base_processor import BaseNotesProcessor
from notes_generator.processors.pdf_processor import PDFNotesProcessor
from notes_generator.processors.transcript_processor import TranscriptNotesProcessor

__all__ = ['BaseNotesProcessor', 'PDFNotesProcessor', 'TranscriptNotesProcessor']

