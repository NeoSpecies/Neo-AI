"""Base adapter class for AI models"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional


class ModelAdapter(ABC):
    """Abstract base class for AI model adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    @abstractmethod
    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion"""
        pass
        
    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming chat completion"""
        pass
        
    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate image from text prompt"""
        pass
        
    @abstractmethod
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """Transcribe audio to text"""
        pass
        
    @abstractmethod
    async def generate_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """Generate speech from text"""
        pass
        
    @abstractmethod
    async def create_embedding(self, texts: List[str], **kwargs) -> Dict[str, Any]:
        """Create text embeddings"""
        pass
        
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if adapter supports streaming"""
        pass
        
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        pass
        
    def validate_config(self) -> None:
        """Validate adapter configuration"""
        required_fields = self.get_required_config_fields()
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
                
    @abstractmethod
    def get_required_config_fields(self) -> List[str]:
        """Get list of required configuration fields"""
        pass