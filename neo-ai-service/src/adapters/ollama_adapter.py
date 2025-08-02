"""Ollama adapter implementation for local models"""

import logging
import httpx
from typing import List, Dict, Any, AsyncIterator, Optional
from .base import ModelAdapter

logger = logging.getLogger(__name__)


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama local models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config()
        
        # Ollama API endpoint
        self.api_base = config.get('api_base', 'http://localhost:11434')
        self.timeout = config.get('timeout', 60.0)
        
        # Create async HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            timeout=httpx.Timeout(self.timeout)
        )
        
    def get_required_config_fields(self) -> List[str]:
        """Ollama only requires api_base"""
        return []  # api_base has default value
        
    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Ollama"""
        try:
            # Get model name
            model = kwargs.get('model', 'llama2')
            
            # Prepare request
            request_data = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get('temperature', 0.7),
                    "top_p": kwargs.get('top_p', 1.0),
                    "num_predict": kwargs.get('max_tokens', -1),
                }
            }
            
            # Call Ollama API
            response = await self.client.post(
                "/api/chat",
                json=request_data
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Format response similar to OpenAI
            return {
                "content": result.get("message", {}).get("content", ""),
                "model": model,
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                    "total_cost": 0.0  # Ollama is free
                }
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
            
    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming chat completion"""
        try:
            model = kwargs.get('model', 'llama2')
            
            request_data = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": kwargs.get('temperature', 0.7),
                    "top_p": kwargs.get('top_p', 1.0),
                    "num_predict": kwargs.get('max_tokens', -1),
                }
            }
            
            # Stream response
            async with self.client.stream("POST", "/api/chat", json=request_data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        
                        if data.get("done", False):
                            break
                            
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield {
                                "delta": content,
                                "model": model
                            }
                            
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise
            
    async def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Ollama doesn't support image generation"""
        raise NotImplementedError("Ollama does not support image generation")
        
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """Ollama doesn't support audio transcription"""
        raise NotImplementedError("Ollama does not support audio transcription")
        
    async def generate_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """Ollama doesn't support speech generation"""
        raise NotImplementedError("Ollama does not support speech generation")
        
    async def create_embedding(self, texts: List[str], **kwargs) -> Dict[str, Any]:
        """Create embeddings using Ollama"""
        try:
            model = kwargs.get('model', 'llama2')
            
            embeddings = []
            for text in texts:
                response = await self.client.post(
                    "/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                embeddings.append(result.get("embedding", []))
                
            return {
                "embeddings": embeddings,
                "model": model,
                "usage": {
                    "total_tokens": 0  # Ollama doesn't provide token count for embeddings
                }
            }
            
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise
            
    def supports_streaming(self) -> bool:
        """Ollama supports streaming"""
        return True
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information"""
        return {
            "provider": "ollama",
            "models": {
                "chat": ["llama2", "codellama", "mistral", "mixtral", "gemma", "qwen"],
                "embedding": ["llama2", "codellama", "mistral"]
            },
            "supports_streaming": True,
            "supports_functions": False,
            "local": True,
            "free": True
        }
        
    async def list_local_models(self) -> List[str]:
        """List available models in Ollama"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            return [model.get("name") for model in models if model.get("name")]
            
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
            
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client"""
        await self.client.aclose()