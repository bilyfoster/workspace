"""Configuration management for Herbie"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Load and manage Herbie configuration"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'ollama.host')"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    @property
    def ollama_host(self) -> str:
        return self.get('ollama.host', 'http://localhost:11434')
    
    @property
    def default_model(self) -> str:
        return self.get('ollama.default_model', 'gemma3:latest')
    
    @property
    def orchestrator_model(self) -> str:
        return self.get('ollama.orchestrator_model', 'qwen3.5:9b')
    
    def reload(self):
        """Reload configuration from file"""
        self._config = self._load()

# Global config instance
config = Config()
