import os
import json
import logging
import argparse
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_path: str = None, initial_config: Dict = None):
        """
        Initializes the Config object for extraction parameters.
        
        Args:
            config_path: Path to a JSON configuration file
            initial_config: Dictionary to initialize config with (skips file loading)
        """
        self.default_config = {
            "pages_per_chunk": 10,
            "lines_per_chunk": 120,
            "screenshots_per_minute": 1.0,  # can be lower than 1.0
            "include_pdf_images": True,
            "hash_similarity_threshold": 5, # for screenshots deduplication
            "min_diversity_threshold": 10,  # for screenshots deduplication
            "output_prefix": "refined"
        }
        
        if initial_config:
            self.config = initial_config
        else:
            self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Loads configuration from file and defaults."""
        config = self.default_config.copy()

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config.update(json.load(f))
            except json.JSONDecodeError:
                logger.error(f"Error decoding {config_path}. Using default config.", exc_info=True)
        
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a value from the config."""
        return self.config.get(key, default)

    def update_from_args(self, args: argparse.Namespace):
        """
        Updates the configuration from parsed command-line arguments.
        
        Args:
            args: Parsed command-line arguments from argparse
        """
        arg_to_config_map = {
            "pages_per_chunk": "pages_per_chunk",
            "lines_per_chunk": "lines_per_chunk",
            "screenshots_per_minute": "screenshots_per_minute",
            "hash_similarity_threshold": "hash_similarity_threshold",
            "min_diversity_threshold": "min_diversity_threshold",
            "output_prefix": "output_prefix",
        }
        
        for arg_key, config_key in arg_to_config_map.items():
            value = getattr(args, arg_key, None)
            if value is not None:
                self.config[config_key] = value

    def save(self, path):
        try:
            config_to_save = self.config.copy()
            with open(path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config file: {e}")