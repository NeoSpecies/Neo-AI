"""OpenRouter adapter using httpx for Python 3.13 compatibility"""

import json
import logging
from typing import Dict, Any, List, AsyncIterator, Optional
import httpx
from .base import ModelAdapter

logger = logging.getLogger(__name__)


class OpenRouterAdapter(ModelAdapter):
    """Adapter for OpenRouter API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config()
        
        # API configuration
        self.api_key = config.get('api_key')
        self.api_base = config.get('api_base', 'https://openrouter.ai/api/v1')
        self.timeout = config.get('timeout', 60.0)
        self.extra_headers = config.get('extra_headers', {})
        
        # Default headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers
        }
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            headers=self.headers,
            timeout=httpx.Timeout(self.timeout)
        )
        
    def get_required_config_fields(self) -> List[str]:
        """OpenRouter requires api_key"""
        return ['api_key']
        
    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using OpenRouter"""
        try:
            # Prepare request
            data = {
                "model": kwargs.get('model', 'openai/gpt-3.5-turbo'),
                "messages": messages,
                "temperature": kwargs.get('temperature', 0.7),
                "max_tokens": kwargs.get('max_tokens'),
                "top_p": kwargs.get('top_p'),
                "frequency_penalty": kwargs.get('frequency_penalty', 0),
                "presence_penalty": kwargs.get('presence_penalty', 0),
                "stream": False
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Make request
            response = await self.client.post(
                "/chat/completions",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Format response similar to OpenAI
            return {
                "content": result['choices'][0]['message']['content'],
                "model": result.get('model', data['model']),
                "finish_reason": result['choices'][0].get('finish_reason', 'stop'),
                "usage": result.get('usage', {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                })
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter chat error: {e}")
            raise
            
    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming chat completion"""
        try:
            data = {
                "model": kwargs.get('model', 'openai/gpt-3.5-turbo'),
                "messages": messages,
                "temperature": kwargs.get('temperature', 0.7),
                "max_tokens": kwargs.get('max_tokens'),
                "stream": True
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Stream response
            async with self.client.stream('POST', '/chat/completions', json=data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        line_data = line[6:]  # Remove 'data: ' prefix
                        
                        if line_data == '[DONE]':
                            break
                            
                        try:
                            chunk = json.loads(line_data)
                            if chunk['choices'][0]['delta'].get('content'):
                                yield {
                                    "delta": chunk['choices'][0]['delta']['content'],
                                    "model": chunk.get('model', data['model'])
                                }
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"OpenRouter streaming error: {e}")
            raise
            
    async def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image using OpenRouter (if supported models available)"""
        try:
            model = kwargs.get('model', 'openai/dall-e-3')
            
            data = {
                "model": model,
                "prompt": prompt,
                "size": kwargs.get('size', '1024x1024'),
                "quality": kwargs.get('quality', 'standard'),
                "n": kwargs.get('n', 1)
            }
            
            response = await self.client.post(
                "/images/generations",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            images = []
            for img in result.get('data', []):
                image_data = {"revised_prompt": prompt}
                if 'b64_json' in img:
                    image_data["base64"] = img['b64_json']
                elif 'url' in img:
                    image_data["url"] = img['url']
                images.append(image_data)
                
            return {
                "images": images,
                "model": model,
                "cost": 0.0  # OpenRouter pricing varies
            }
            
        except Exception as e:
            logger.error(f"OpenRouter image generation error: {e}")
            raise
            
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """OpenRouter doesn't directly support audio transcription"""
        raise NotImplementedError("Audio transcription not available through OpenRouter")
        
    async def generate_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """OpenRouter doesn't directly support speech generation"""
        raise NotImplementedError("Speech generation not available through OpenRouter")
        
    async def create_embedding(self, texts: List[str], **kwargs) -> Dict[str, Any]:
        """Create embeddings using OpenRouter"""
        try:
            model = kwargs.get('model', 'openai/text-embedding-ada-002')
            
            embeddings = []
            for text in texts:
                data = {
                    "model": model,
                    "input": text
                }
                
                response = await self.client.post(
                    "/embeddings",
                    json=data
                )
                response.raise_for_status()
                
                result = response.json()
                embeddings.append(result['data'][0]['embedding'])
                
            return {
                "embeddings": embeddings,
                "model": model,
                "usage": {"total_tokens": 0}
            }
            
        except Exception as e:
            logger.error(f"OpenRouter embedding error: {e}")
            raise
            
    def supports_streaming(self) -> bool:
        """OpenRouter supports streaming"""
        return True
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenRouter model information"""
        return {
            "provider": "openrouter",
            "models": {
                "chat": [
                    # OpenAI models
                    "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-4-turbo",
                    "openai/gpt-3.5-turbo", "openai/gpt-4",
                    # Anthropic models
                    "anthropic/claude-3-opus", "anthropic/claude-3-sonnet",
                    "anthropic/claude-3-haiku", "anthropic/claude-2.1",
                    # Google models
                    "google/gemini-pro", "google/gemini-pro-vision",
                    # Meta models
                    "meta-llama/llama-3-70b-instruct", "meta-llama/llama-3-8b-instruct",
                    # Mistral models
                    "mistralai/mistral-7b-instruct", "mistralai/mixtral-8x7b-instruct",
                    # And many more...
                ],
                "image": ["openai/dall-e-3", "openai/dall-e-2"],
                "embedding": ["openai/text-embedding-ada-002", "openai/text-embedding-3-small"]
            },
            "supports_streaming": True,
            "supports_functions": True,
            "note": "OpenRouter provides access to 300+ AI models through a single API"
        }
        
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available models from OpenRouter"""
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
                
        except Exception as e:
            logger.error(f"Failed to list OpenRouter models: {e}")
            return []
            
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client"""
        await self.client.aclose()