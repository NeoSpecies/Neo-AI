"""Chat request handler"""

import logging
import time
import hashlib
import json
from typing import Dict, Any, List, Optional
from adapters.base import ModelAdapter

logger = logging.getLogger(__name__)


class ChatHandler:
    """Handler for chat requests"""
    
    def __init__(self, adapters: Dict[str, ModelAdapter]):
        self.adapters = adapters
        
        # Components (set via set_components)
        self.cache_manager = None
        self.rate_limiter = None
        self.model_router = None
        self.error_handler = None
        self.performance_monitor = None
        
    def set_components(self, **components):
        """Set references to service components"""
        self.cache_manager = components.get('cache_manager')
        self.rate_limiter = components.get('rate_limiter')
        self.model_router = components.get('model_router')
        self.error_handler = components.get('error_handler')
        self.performance_monitor = components.get('performance_monitor')
        
    async def handle_chat(self, params: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
        """Handle chat completion request"""
        start_time = time.time()
        
        try:
            # Extract parameters
            messages = params.get('messages', [])
            requested_model = params.get('model')
            stream = params.get('stream', False)
            
            # Validate messages
            if not messages:
                return {
                    "status": "error",
                    "error": "No messages provided"
                }
            
            # Check cache if enabled
            cache_key = None
            if self.cache_manager and not stream:
                cache_key = self._generate_cache_key(messages, requested_model, params)
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for model {requested_model}")
                    return {
                        "status": "success",
                        "data": cached_result,
                        "cached": True
                    }
            
            # Use model router if available
            if self.model_router:
                model, adapter_name = self.model_router.select_model(
                    messages, requested_model, metadata
                )
                adapter = self.adapters.get(adapter_name)
            else:
                # Fallback to original selection logic
                model = requested_model or 'gpt-3.5-turbo'
                adapter = self._select_adapter(model)
                adapter_name = self._get_adapter_name(adapter)
            
            if not adapter:
                return {
                    "status": "error",
                    "error": f"No adapter available for model: {model}"
                }
                
            # Prepare parameters for adapter
            adapter_params = {k: v for k, v in params.items() 
                            if k not in ['messages', 'stream']}
            adapter_params['model'] = model  # Use selected model
                
            # Handle streaming vs non-streaming
            if stream:
                # For streaming, we need to handle this differently
                # This would be handled by the service layer
                return {
                    "status": "streaming",
                    "adapter": adapter,
                    "adapter_name": adapter_name,
                    "params": adapter_params
                }
            else:
                # Non-streaming chat with retry logic
                try:
                    result = await adapter.chat(messages, **adapter_params)
                    
                    # Record success
                    response_time = time.time() - start_time
                    if self.model_router:
                        self.model_router.record_success(model, response_time)
                    
                    # Cache result if enabled
                    if self.cache_manager and cache_key:
                        await self.cache_manager.set(cache_key, result)
                    
                    return {
                        "status": "success",
                        "data": result,
                        "adapter_name": adapter_name
                    }
                    
                except Exception as adapter_error:
                    # Record failure
                    if self.model_router:
                        self.model_router.record_failure(model)
                        
                        # Try fallback model
                        fallback_info = self.model_router.get_fallback_model(model)
                        if fallback_info:
                            fallback_model, fallback_adapter_name = fallback_info
                            fallback_adapter = self.adapters.get(fallback_adapter_name)
                            
                            if fallback_adapter:
                                logger.warning(f"Falling back from {model} to {fallback_model}")
                                adapter_params['model'] = fallback_model
                                
                                try:
                                    result = await fallback_adapter.chat(messages, **adapter_params)
                                    return {
                                        "status": "success",
                                        "data": result,
                                        "adapter_name": fallback_adapter_name,
                                        "fallback_used": True,
                                        "original_model": model
                                    }
                                except Exception as fallback_error:
                                    logger.error(f"Fallback also failed: {fallback_error}")
                    
                    raise adapter_error
                
        except Exception as e:
            logger.error(f"Chat handler error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _select_adapter(self, model: str) -> Optional[ModelAdapter]:
        """Select appropriate adapter based on model name"""
        # OpenRouter models - any model with "/" is from OpenRouter
        # This includes models like "openai/gpt-3.5-turbo", "cognitivecomputations/dolphin:free", etc.
        if '/' in model:
            return self.adapters.get('openrouter')
            
        # Check for local models (Ollama) - models without "/" are local
        # Examples: "gemma3:12b", "llama2", "codellama", etc.
        if ':' in model or model in ['llama2', 'codellama', 'mistral', 'mixtral', 'gemma', 'qwen']:
            return self.adapters.get('ollama')
            
        # Legacy OpenAI direct models (if using OpenAI adapter directly)
        if model.startswith('gpt') or model.startswith('dall-e') or model == 'whisper-1':
            return self.adapters.get('openai')
            
        # Legacy Anthropic direct models    
        elif model.startswith('claude'):
            return self.adapters.get('anthropic')
            
        # Legacy Google direct models    
        elif model.startswith('gemini'):
            return self.adapters.get('google')
            
        # Check if model exists in Ollama (for custom models)
        if 'ollama' in self.adapters:
            return self.adapters.get('ollama')
            
        # Default to OpenAI
        return self.adapters.get('openai')
    
    def _get_adapter_name(self, adapter: Optional[ModelAdapter]) -> Optional[str]:
        """Get adapter name from adapter instance"""
        if not adapter:
            return None
        
        for name, ad in self.adapters.items():
            if ad == adapter:
                return name
        
        return None
    
    def _generate_cache_key(self, messages: List[Dict[str, Any]], model: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        # Create a deterministic string from messages and params
        cache_data = {
            "messages": messages,
            "model": model,
            "params": {k: v for k, v in params.items() if k not in ['messages', 'model', 'stream']}
        }
        
        # Hash the data
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()