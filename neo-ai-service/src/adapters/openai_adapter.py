"""OpenAI adapter implementation"""

import os
import base64
import logging
from typing import List, Dict, Any, AsyncIterator, Optional
from openai import AsyncOpenAI
from .base import ModelAdapter

logger = logging.getLogger(__name__)


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config()
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=config.get('api_key') or os.getenv('OPENAI_API_KEY'),
            base_url=config.get('api_base'),
            timeout=config.get('timeout', 60.0),
            max_retries=config.get('max_retries', 3)
        )
        
    def get_required_config_fields(self) -> List[str]:
        """OpenAI requires api_key"""
        return []  # api_key can come from environment
        
    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using OpenAI"""
        try:
            # Prepare messages
            formatted_messages = self._format_messages(messages)
            
            # Set default model if not specified
            model = kwargs.get('model', 'gpt-3.5-turbo')
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens'),
                top_p=kwargs.get('top_p'),
                frequency_penalty=kwargs.get('frequency_penalty', 0),
                presence_penalty=kwargs.get('presence_penalty', 0),
                stream=False
            )
            
            # Format response
            choice = response.choices[0]
            return {
                "content": choice.message.content,
                "model": response.model,
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "total_cost": self._calculate_cost(
                        response.model,
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise
            
    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming chat completion"""
        try:
            formatted_messages = self._format_messages(messages)
            model = kwargs.get('model', 'gpt-3.5-turbo')
            
            # Create streaming response
            stream = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens'),
                stream=True
            )
            
            # Stream chunks
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "delta": chunk.choices[0].delta.content,
                        "model": model
                    }
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
            
    async def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image using DALL-E"""
        try:
            model = kwargs.get('model', 'dall-e-3')
            
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                size=kwargs.get('size', '1024x1024'),
                quality=kwargs.get('quality', 'standard'),
                style=kwargs.get('style', 'vivid'),
                n=kwargs.get('n', 1),
                response_format=kwargs.get('response_format', 'b64_json')
            )
            
            images = []
            for img in response.data:
                image_data = {
                    "revised_prompt": getattr(img, 'revised_prompt', prompt)
                }
                
                if hasattr(img, 'b64_json'):
                    image_data["base64"] = img.b64_json
                elif hasattr(img, 'url'):
                    image_data["url"] = img.url
                    
                images.append(image_data)
                
            return {
                "images": images,
                "model": model,
                "cost": self._calculate_image_cost(model, kwargs.get('quality', 'standard'))
            }
            
        except Exception as e:
            logger.error(f"OpenAI image generation error: {e}")
            raise
            
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        try:
            # Create a file-like object from bytes
            import io
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"  # OpenAI requires a filename
            
            response = await self.client.audio.transcriptions.create(
                model=kwargs.get('model', 'whisper-1'),
                file=audio_file,
                language=kwargs.get('language'),
                response_format=kwargs.get('format', 'text')
            )
            
            return {
                "text": response if isinstance(response, str) else response.text,
                "model": "whisper-1"
            }
            
        except Exception as e:
            logger.error(f"OpenAI transcription error: {e}")
            raise
            
    async def generate_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """Generate speech using TTS"""
        try:
            response = await self.client.audio.speech.create(
                model=kwargs.get('model', 'tts-1'),
                voice=kwargs.get('voice', 'alloy'),
                input=text,
                speed=kwargs.get('speed', 1.0)
            )
            
            # Read the response content
            audio_data = b""
            async for chunk in response.iter_bytes():
                audio_data += chunk
                
            return {
                "audio": base64.b64encode(audio_data).decode('utf-8'),
                "model": kwargs.get('model', 'tts-1'),
                "voice": kwargs.get('voice', 'alloy')
            }
            
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise
            
    async def create_embedding(self, texts: List[str], **kwargs) -> Dict[str, Any]:
        """Create embeddings"""
        try:
            model = kwargs.get('model', 'text-embedding-ada-002')
            
            response = await self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            
            return {
                "embeddings": embeddings,
                "model": model,
                "usage": {
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
            
    def supports_streaming(self) -> bool:
        """OpenAI supports streaming"""
        return True
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "openai",
            "models": {
                "chat": ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"],
                "image": ["dall-e-3", "dall-e-2"],
                "audio": ["whisper-1"],
                "tts": ["tts-1", "tts-1-hd"],
                "embedding": ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
            },
            "supports_streaming": True,
            "supports_functions": True
        }
        
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format messages for OpenAI API"""
        formatted = []
        
        for msg in messages:
            formatted_msg = {
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            }
            
            # Handle multimodal messages
            if "images" in msg and msg["images"]:
                content = [{"type": "text", "text": msg["content"]}]
                
                for image in msg["images"]:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image}"
                        }
                    })
                    
                formatted_msg["content"] = content
                
            formatted.append(formatted_msg)
            
        return formatted
        
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage"""
        # Pricing as of 2024 (in USD per 1K tokens)
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
        }
        
        # Default pricing if model not found
        model_pricing = pricing.get(model, {"input": 0.0005, "output": 0.0015})
        
        input_cost = (prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (completion_tokens / 1000) * model_pricing["output"]
        
        return round(input_cost + output_cost, 6)
        
    def _calculate_image_cost(self, model: str, quality: str) -> float:
        """Calculate image generation cost"""
        # DALL-E 3 pricing
        if model == "dall-e-3":
            return 0.04 if quality == "standard" else 0.08
        # DALL-E 2 pricing
        elif model == "dall-e-2":
            return 0.02
        return 0.0