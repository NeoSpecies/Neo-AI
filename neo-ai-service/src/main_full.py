"""Main entry point for Neo AI Service"""

import asyncio
import json
import signal
import sys
import os
from typing import Dict, Any

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ipc import NeoIPCClient
from adapters import OpenAIAdapter, OllamaAdapter, OpenRouterAdapter
from handlers import ChatHandler
from utils import Config, setup_logger

# Global logger
logger = None


class AIService:
    """Main AI Service class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.adapters = {}
        self.handlers = {}
        self.running = False
        
    async def initialize(self):
        """Initialize the service"""
        logger.info("Initializing AI Service...")
        
        # Initialize IPC client
        ipc_config = self.config.get('ipc', {})
        self.client = NeoIPCClient(
            host=ipc_config.get('host', 'localhost'),
            port=ipc_config.get('port', 9999)
        )
        
        # Initialize adapters
        await self._init_adapters()
        
        # Initialize handlers
        self._init_handlers()
        
        # Register IPC handlers
        self._register_ipc_handlers()
        
        logger.info("AI Service initialized successfully")
        
    async def _init_adapters(self):
        """Initialize AI model adapters"""
        # OpenAI adapter
        openai_config = self.config.get_provider_config('openai')
        if openai_config.get('api_key'):
            try:
                self.adapters['openai'] = OpenAIAdapter(openai_config)
                logger.info("OpenAI adapter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI adapter: {e}")
                
        # Ollama adapter
        ollama_config = self.config.get_provider_config('ollama')
        try:
            self.adapters['ollama'] = OllamaAdapter(ollama_config)
            logger.info("Ollama adapter initialized")
            
            # List available models
            models = await self.adapters['ollama'].list_local_models()
            if models:
                logger.info(f"Available Ollama models: {', '.join(models)}")
            else:
                logger.warning("No Ollama models found. Run 'ollama pull llama2' to download models.")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama adapter: {e}")
            
        # OpenRouter adapter
        openrouter_config = self.config.get_provider_config('openrouter')
        if openrouter_config.get('api_key'):
            try:
                self.adapters['openrouter'] = OpenRouterAdapter(openrouter_config)
                logger.info("OpenRouter adapter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenRouter adapter: {e}")
                
    def _init_handlers(self):
        """Initialize request handlers"""
        self.handlers['chat'] = ChatHandler(self.adapters)
        
    def _register_ipc_handlers(self):
        """Register IPC method handlers"""
        
        @self.client.handler("chat")
        async def handle_chat(params: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
            """Handle chat requests"""
            logger.info(f"Received chat request: {params.get('model', 'default')}")
            
            result = await self.handlers['chat'].handle_chat(params, metadata)
            
            # Handle streaming response
            if result.get('status') == 'streaming':
                # For now, convert to non-streaming
                # TODO: Implement proper streaming support
                adapter = result['adapter']
                messages = result['params']['messages']
                response = await adapter.chat(messages, **result['params'])
                return {
                    "status": "success",
                    "data": response
                }
                
            return result
            
        @self.client.handler("generate_image")
        async def handle_generate_image(params: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
            """Handle image generation requests"""
            logger.info("Received image generation request")
            
            try:
                prompt = params.get('prompt', '')
                if not prompt:
                    return {"status": "error", "error": "No prompt provided"}
                    
                adapter = self.adapters.get('openai')
                if not adapter:
                    return {"status": "error", "error": "No adapter available for image generation"}
                    
                result = await adapter.generate_image(prompt, **params)
                
                return {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(f"Image generation error: {e}")
                return {"status": "error", "error": str(e)}
                
        @self.client.handler("list_models")
        async def handle_list_models(params: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
            """List available models"""
            logger.info("Received list_models request")
            
            models = {}
            for name, adapter in self.adapters.items():
                models[name] = adapter.get_model_info()
                
            return {
                "status": "success",
                "data": {
                    "providers": models,
                    "defaults": self.config.get('defaults', {})
                }
            }
            
        @self.client.handler("health")
        async def handle_health(params: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
            """Health check"""
            health_data = {
                "healthy": True,
                "service": "ai-service",
                "version": self.config.get('service.version', '1.0.0'),
                "adapters": list(self.adapters.keys())
            }
            
            # Add component health
            if self.cache_manager:
                health_data["cache"] = self.cache_manager.get_stats()
            if self.rate_limiter:
                health_data["rate_limiter"] = self.rate_limiter.get_stats()
            if self.model_router:
                health_data["router"] = self.model_router.get_stats()
            if self.error_handler:
                health_data["errors"] = self.error_handler.get_stats()
            if self.performance_monitor:
                health_data["metrics"] = self.performance_monitor.get_metrics_summary()
            
            return {
                "status": "success",
                "data": health_data
            }
            
        @self.client.handler("metrics")
        async def handle_metrics(params: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
            """Get performance metrics"""
            if not self.performance_monitor:
                return {
                    "status": "error",
                    "error": "Performance monitoring not enabled"
                }
            
            return {
                "status": "success",
                "data": self.performance_monitor.get_metrics_summary()
            }
            
    async def start(self):
        """Start the service"""
        try:
            # Connect to Neo Framework
            await self.client.connect()
            
            # Register service
            service_metadata = {
                "version": self.config.get('service.version', '1.0.0'),
                "protocol": "ipc",
                "language": "python",
                "capabilities": json.dumps([
                    "chat", "generate_image", "list_models", "health"
                ])
            }
            
            await self.client.register_service(
                self.config.get('service.name', 'ai-service'),
                service_metadata
            )
            
            logger.info("AI Service registered with Neo Framework")
            
            # Run service
            self.running = True
            await self.client.run()
            
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
            
    async def stop(self):
        """Stop the service"""
        logger.info("Stopping AI Service...")
        self.running = False
        
        if self.client:
            await self.client.disconnect()
            
        logger.info("AI Service stopped")


async def main():
    """Main function"""
    global logger
    
    # Load configuration
    config = Config()
    
    # Setup logging
    logger = setup_logger(
        "ai-service",
        config.get('service.log_level', 'INFO')
    )
    
    logger.info("=" * 50)
    logger.info("Neo AI Service Starting")
    logger.info("=" * 50)
    
    # Create service
    service = AIService(config)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(service.stop())
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start service
        await service.initialize()
        await service.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Service failed: {e}", exc_info=True)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())