"""Intelligent model router for AI Service"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from .model_selector import ModelSelector, TaskType

logger = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    """Router configuration"""
    enabled: bool = True
    enable_fallback: bool = True
    max_fallback_attempts: int = 3
    
    # Routing preferences
    prefer_local: bool = True
    cost_sensitive: bool = True
    quality_priority: bool = False
    speed_priority: bool = False
    
    # Load balancing
    enable_load_balancing: bool = True
    load_balance_strategy: str = "round_robin"  # round_robin, least_loaded, random
    
    # Model health tracking
    track_model_health: bool = True
    failure_threshold: int = 3  # Failures before marking unhealthy
    recovery_time: int = 300  # Seconds before retrying unhealthy model


@dataclass
class ModelHealth:
    """Track model health status"""
    failures: int = 0
    successes: int = 0
    last_failure: Optional[float] = None
    last_success: Optional[float] = None
    response_times: List[float] = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
            
    @property
    def is_healthy(self) -> bool:
        """Check if model is healthy"""
        if self.failures >= 3 and self.last_failure:
            # Check if enough time has passed for recovery
            recovery_time = 300  # 5 minutes
            if time.time() - self.last_failure < recovery_time:
                return False
        return True
        
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0
        
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        if not self.response_times:
            return 0
        return sum(self.response_times) / len(self.response_times)
        
    def record_success(self, response_time: float):
        """Record successful request"""
        self.successes += 1
        self.last_success = time.time()
        self.failures = 0  # Reset failure count
        
        # Keep last 100 response times
        self.response_times.append(response_time)
        if len(self.response_times) > 100:
            self.response_times.pop(0)
            
    def record_failure(self):
        """Record failed request"""
        self.failures += 1
        self.last_failure = time.time()


class ModelRouter:
    """Routes requests to appropriate models with intelligent selection"""
    
    def __init__(self, config: RouterConfig, adapters: Dict[str, Any]):
        self.config = config
        self.adapters = adapters
        self.selector = ModelSelector()
        
        # Model health tracking
        self.model_health: Dict[str, ModelHealth] = defaultdict(ModelHealth)
        
        # Load balancing state
        self.round_robin_index: Dict[str, int] = defaultdict(int)
        
        # Statistics
        self.routing_stats = defaultdict(lambda: {"routed": 0, "fallback": 0, "failed": 0})
        
    def select_model(
        self,
        messages: List[Dict[str, Any]],
        requested_model: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        """
        Select the best model for the request
        
        Args:
            messages: Chat messages
            requested_model: User-requested model (optional)
            metadata: Additional request metadata
            
        Returns:
            Tuple of (selected_model, selected_adapter)
        """
        if not self.config.enabled:
            # Routing disabled, use requested model or default
            if requested_model:
                adapter = self._get_adapter_for_model(requested_model)
                return requested_model, adapter
            else:
                # Default to first available
                return self._get_default_model()
                
        # If specific model requested, try to use it
        if requested_model:
            adapter = self._get_adapter_for_model(requested_model)
            if adapter and self._is_model_available(requested_model):
                logger.debug(f"Using requested model: {requested_model}")
                return requested_model, adapter
                
        # Analyze task type
        task_type = self.selector.analyze_task(messages)
        logger.debug(f"Detected task type: {task_type.value}")
        
        # Get available models
        available_models = self._get_available_models()
        
        # Build preferences based on config and metadata
        preferences = {
            "cost_sensitive": self.config.cost_sensitive,
            "quality_priority": self.config.quality_priority,
            "speed_priority": self.config.speed_priority,
            "prefer_local": self.config.prefer_local,
        }
        
        # Override with metadata preferences if provided
        if metadata:
            preferences.update(metadata.get("routing_preferences", {}))
            
        # Select model
        selected_model = self.selector.select_model(task_type, available_models, preferences)
        
        if selected_model:
            adapter = self._get_adapter_for_model(selected_model)
            logger.info(f"Routed to model: {selected_model} (task: {task_type.value})")
            self.routing_stats[selected_model]["routed"] += 1
            return selected_model, adapter
            
        # Fallback to default
        return self._get_default_model()
        
    def get_fallback_model(self, failed_model: str) -> Optional[Tuple[str, str]]:
        """
        Get fallback model when primary fails
        
        Args:
            failed_model: Model that failed
            
        Returns:
            Tuple of (fallback_model, adapter) or None
        """
        if not self.config.enable_fallback:
            return None
            
        # Record failure
        self.model_health[failed_model].record_failure()
        
        # Get fallback models
        fallbacks = self.selector.get_fallback_models(failed_model)
        
        # Filter available and healthy fallbacks
        for fallback in fallbacks:
            if self._is_model_available(fallback):
                adapter = self._get_adapter_for_model(fallback)
                if adapter:
                    logger.info(f"Using fallback model: {fallback} (primary: {failed_model})")
                    self.routing_stats[failed_model]["fallback"] += 1
                    return fallback, adapter
                    
        logger.error(f"No fallback available for {failed_model}")
        self.routing_stats[failed_model]["failed"] += 1
        return None
        
    def record_success(self, model: str, response_time: float):
        """Record successful model usage"""
        self.model_health[model].record_success(response_time)
        
    def record_failure(self, model: str):
        """Record model failure"""
        self.model_health[model].record_failure()
        
    def _get_available_models(self) -> List[str]:
        """Get list of available and healthy models"""
        models = []
        
        # Check Ollama models
        if "ollama" in self.adapters:
            # TODO: Get actual available models from adapter
            ollama_models = ["gemma3:12b", "llama3:8b", "codellama:13b"]
            models.extend(ollama_models)
            
        # Check OpenRouter models
        if "openrouter" in self.adapters:
            # Add known OpenRouter models
            openrouter_models = [
                "openai/gpt-3.5-turbo",
                "openai/gpt-4",
                "anthropic/claude-3-haiku",
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
            ]
            models.extend(openrouter_models)
            
        # Filter healthy models if health tracking enabled
        if self.config.track_model_health:
            models = [m for m in models if self.model_health[m].is_healthy]
            
        return models
        
    def _is_model_available(self, model: str) -> bool:
        """Check if model is available and healthy"""
        if self.config.track_model_health and not self.model_health[model].is_healthy:
            return False
            
        adapter = self._get_adapter_for_model(model)
        return adapter is not None
        
    def _get_adapter_for_model(self, model: str) -> Optional[str]:
        """Get adapter name for a model"""
        # Check if it's an OpenRouter model (contains /)
        if "/" in model:
            return "openrouter" if "openrouter" in self.adapters else None
            
        # Check if it's an Ollama model
        if ":" in model or model in ["llama2", "codellama", "mistral", "mixtral", "gemma", "qwen"]:
            return "ollama" if "ollama" in self.adapters else None
            
        # Try to match by model name patterns
        if model.startswith("gpt"):
            return "openai" if "openai" in self.adapters else "openrouter"
        elif model.startswith("claude"):
            return "anthropic" if "anthropic" in self.adapters else "openrouter"
            
        return None
        
    def _get_default_model(self) -> Tuple[str, str]:
        """Get default model and adapter"""
        # Prefer local Ollama if available
        if self.config.prefer_local and "ollama" in self.adapters:
            return "gemma3:12b", "ollama"
            
        # Otherwise use OpenRouter
        if "openrouter" in self.adapters:
            return "openai/gpt-3.5-turbo", "openrouter"
            
        # Fallback to first available adapter
        if self.adapters:
            adapter = list(self.adapters.keys())[0]
            if adapter == "ollama":
                return "gemma3:12b", adapter
            else:
                return "openai/gpt-3.5-turbo", adapter
                
        raise ValueError("No adapters available")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        total_routed = sum(stats["routed"] for stats in self.routing_stats.values())
        total_fallback = sum(stats["fallback"] for stats in self.routing_stats.values())
        total_failed = sum(stats["failed"] for stats in self.routing_stats.values())
        
        model_stats = []
        for model, health in self.model_health.items():
            model_stats.append({
                "model": model,
                "healthy": health.is_healthy,
                "success_rate": health.success_rate,
                "avg_response_time": health.avg_response_time,
                "failures": health.failures,
                "successes": health.successes
            })
            
        return {
            "enabled": self.config.enabled,
            "total_requests": total_routed,
            "fallback_used": total_fallback,
            "failed_routing": total_failed,
            "model_health": model_stats,
            "routing_preferences": {
                "prefer_local": self.config.prefer_local,
                "cost_sensitive": self.config.cost_sensitive,
                "quality_priority": self.config.quality_priority,
                "speed_priority": self.config.speed_priority
            }
        }