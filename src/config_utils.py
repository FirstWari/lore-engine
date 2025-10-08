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
        Initializes the Config object, loading from a file if provided.
        API keys are loaded separately for security.
        
        Args:
            config_path: Path to a JSON configuration file
            initial_config: Dictionary to initialize config with (skips file loading)
        """
        self.default_config = {
            # api_key is now loaded separately
            "model_name": "gemini-2.5-flash",
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 65536,
            "pages_per_chunk": 5,
            "lines_per_chunk": 50,
            "screenshots_per_minute": 1.0,  #can be lower than 1.0
            "include_pdf_images": True,
            "hash_similarity_threshold": 5, #for screenshots deduplication
            "min_diversity_threshold": 10,  #for screenshots deduplication
            "api_call_limit_per_file": 10,
            "request_interval": 12,
            "max_retries": 3,
            "retry_delay": 20,
            "output_prefix": "refined"
        }
        
        if initial_config:
            self.config = initial_config
        else:
            self.config = self._load_config(config_path)
            # Only load API keys if not using initial_config (workers already have keys)
            if 'api_key' not in self.config:
                self.config['api_key'] = self._load_api_keys()

    def _load_api_keys(self) -> List[str]:
        """
        Loads API keys from .env file or environment variables.
        
        Looks for .env file in the project root (parent of src/) and loads
        API keys in the format: GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
        
        Fallback: Also supports GEMINI_API_KEY (single key or comma-separated)
        """
        # Load .env file from project root (parent of src/)
        # This works regardless of where the script is run from
        project_root = Path(__file__).parent.parent
        env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
            logger.debug(f"Loaded .env file from {env_path}")
        
        # Try loading numbered API keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...)
        api_keys = []
        idx = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{idx}")
            if key:
                api_keys.append(key.strip())
                idx += 1
            else:
                break
        
        if api_keys:
            logger.info(f"Loaded {len(api_keys)} API key(s) from environment (GEMINI_API_KEY_1, _2, ...)")
            return api_keys
        
        # Fallback to single GEMINI_API_KEY (supports comma-separated)
        env_api_key = os.getenv("GEMINI_API_KEY")
        if env_api_key:
            logger.info("Loaded API keys from GEMINI_API_KEY environment variable.")
            return [key.strip() for key in env_api_key.split(',')]
            
        return []

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

    def get_api_keys(self) -> List[str]:
        """Returns the list of available API keys."""
        keys = self.get("api_key", [])
        return keys if isinstance(keys, list) else [keys]

    def update_from_args(self, args: argparse.Namespace):
        """
        Updates the configuration from parsed command-line arguments.
        
        Args:
            args: Parsed command-line arguments from argparse
        """
        arg_to_config_map = {
            "model": "model_name",
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
        
        # Handle api_key separately due to special processing (comma-separated values)
        if hasattr(args, 'api_key') and args.api_key:
            self.config["api_key"] = [key.strip() for key in args.api_key.split(',')]

    def save(self, path):
        try:
            # Don't save api_key to the config file
            config_to_save = self.config.copy()
            config_to_save.pop('api_key', None)
            with open(path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config file: {e}")