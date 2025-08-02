"""Configuration management for AI Service"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()
        
    def _find_config_file(self) -> str:
        """Find configuration file"""
        # Check environment variable
        if os.getenv('AI_SERVICE_CONFIG'):
            return os.getenv('AI_SERVICE_CONFIG')
            
        # Check common locations
        paths = [
            'config/ai_service.yaml',
            'ai_service.yaml',
            '../config/ai_service.yaml',
            os.path.join(os.path.dirname(__file__), '../../config/ai_service.yaml')
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
                
        # Return default path
        return 'config/ai_service.yaml'
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            # Return default configuration
            return self._get_default_config()
            
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Replace environment variables
            return self._replace_env_vars(config)
            
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()
            
    def _replace_env_vars(self, config: Any) -> Any:
        """Recursively replace environment variables in config"""
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_var = config[2:-1]
            return os.getenv(env_var, config)
        else:
            return config
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'service': {
                'name': 'ai-service',
                'version': '1.0.0',
                'log_level': 'INFO'
            },
            'ipc': {
                'host': os.getenv('NEO_IPC_HOST', 'localhost'),
                'port': int(os.getenv('NEO_IPC_PORT', '9999'))
            },
            'providers': {
                'openai': {
                    'api_key': os.getenv('OPENAI_API_KEY'),
                    'api_base': 'https://api.openai.com/v1',
                    'timeout': 60,
                    'max_retries': 3
                },
                'ollama': {
                    'api_base': 'http://localhost:11434',
                    'timeout': 60
                },
                'openrouter': {
                    'api_key': os.getenv('OPENROUTER_API_KEY'),
                    'api_base': 'https://openrouter.ai/api/v1',
                    'timeout': 60,
                    'extra_headers': {
                        'HTTP-Referer': 'http://localhost:9999',
                        'X-Title': 'Neo AI Service'
                    }
                }
            },
            'defaults': {
                'chat_model': 'gpt-3.5-turbo',
                'temperature': 0.7
            }
        }
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get provider-specific configuration"""
        return self.get(f'providers.{provider}', {})