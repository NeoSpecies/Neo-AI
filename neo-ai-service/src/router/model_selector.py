"""Model selection logic"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of AI tasks"""
    CHAT = "chat"
    CODE = "code"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    MATH = "math"
    GENERAL = "general"


@dataclass
class ModelCapabilities:
    """Model capabilities and characteristics"""
    name: str
    provider: str
    task_types: List[TaskType]
    max_tokens: int
    cost_per_1k_tokens: float  # in USD
    speed_score: float  # 1-10, higher is faster
    quality_score: float  # 1-10, higher is better
    supports_streaming: bool = True
    supports_functions: bool = False
    context_window: int = 4096


class ModelSelector:
    """Intelligent model selection based on task analysis"""
    
    # Model capabilities database
    MODEL_CAPABILITIES = {
        # Ollama models (local, free)
        "gemma3:12b": ModelCapabilities(
            name="gemma3:12b",
            provider="ollama",
            task_types=[TaskType.CHAT, TaskType.GENERAL, TaskType.CREATIVE],
            max_tokens=4096,
            cost_per_1k_tokens=0.0,
            speed_score=8.0,
            quality_score=7.0,
            context_window=8192
        ),
        "llama3:8b": ModelCapabilities(
            name="llama3:8b",
            provider="ollama",
            task_types=[TaskType.CHAT, TaskType.GENERAL],
            max_tokens=4096,
            cost_per_1k_tokens=0.0,
            speed_score=9.0,
            quality_score=6.5,
            context_window=4096
        ),
        "codellama:13b": ModelCapabilities(
            name="codellama:13b",
            provider="ollama",
            task_types=[TaskType.CODE, TaskType.ANALYSIS],
            max_tokens=4096,
            cost_per_1k_tokens=0.0,
            speed_score=7.0,
            quality_score=8.0,
            context_window=4096
        ),
        
        # OpenRouter models
        "openai/gpt-3.5-turbo": ModelCapabilities(
            name="openai/gpt-3.5-turbo",
            provider="openrouter",
            task_types=[TaskType.CHAT, TaskType.GENERAL, TaskType.CREATIVE, TaskType.ANALYSIS],
            max_tokens=4096,
            cost_per_1k_tokens=0.002,
            speed_score=8.0,
            quality_score=8.0,
            supports_functions=True,
            context_window=4096
        ),
        "openai/gpt-4": ModelCapabilities(
            name="openai/gpt-4",
            provider="openrouter",
            task_types=[TaskType.CHAT, TaskType.CODE, TaskType.ANALYSIS, TaskType.MATH, TaskType.CREATIVE],
            max_tokens=8192,
            cost_per_1k_tokens=0.06,
            speed_score=5.0,
            quality_score=10.0,
            supports_functions=True,
            context_window=8192
        ),
        "anthropic/claude-3-haiku": ModelCapabilities(
            name="anthropic/claude-3-haiku",
            provider="openrouter",
            task_types=[TaskType.CHAT, TaskType.GENERAL],
            max_tokens=4096,
            cost_per_1k_tokens=0.001,
            speed_score=9.0,
            quality_score=7.5,
            context_window=100000
        ),
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free": ModelCapabilities(
            name="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            provider="openrouter",
            task_types=[TaskType.CHAT, TaskType.GENERAL, TaskType.CREATIVE],
            max_tokens=4096,
            cost_per_1k_tokens=0.0,
            speed_score=6.0,
            quality_score=7.0,
            context_window=16384
        ),
    }
    
    # Task patterns for detection
    TASK_PATTERNS = {
        TaskType.CODE: [
            r'\b(code|program|function|script|debug|implement|algorithm)\b',
            r'\b(python|javascript|java|c\+\+|golang|rust)\b',
            r'```\w*\n',  # Code blocks
        ],
        TaskType.TRANSLATION: [
            r'\b(translate|translation|翻译|traduire|traducir)\b',
            r'\b(from \w+ to \w+|into \w+)\b',
        ],
        TaskType.SUMMARIZATION: [
            r'\b(summarize|summary|tldr|brief|overview)\b',
            r'\b(main points|key points|highlights)\b',
        ],
        TaskType.CREATIVE: [
            r'\b(write|create|compose|imagine|story|poem|creative)\b',
            r'\b(fiction|narrative|character|plot)\b',
        ],
        TaskType.ANALYSIS: [
            r'\b(analyze|analysis|evaluate|assess|examine)\b',
            r'\b(pros and cons|compare|contrast)\b',
        ],
        TaskType.MATH: [
            r'\b(calculate|solve|equation|math|formula)\b',
            r'\d+\s*[\+\-\*/]\s*\d+',  # Math expressions
            r'\b(derivative|integral|matrix|vector)\b',
        ],
    }
    
    def __init__(self):
        self.task_cache = {}
        
    def analyze_task(self, messages: List[Dict[str, Any]]) -> TaskType:
        """
        Analyze messages to determine task type
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Detected task type
        """
        # Combine all user messages
        combined_text = " ".join(
            msg.get("content", "") 
            for msg in messages 
            if msg.get("role") == "user"
        ).lower()
        
        # Check cache
        cache_key = hash(combined_text)
        if cache_key in self.task_cache:
            return self.task_cache[cache_key]
        
        # Detect task type
        task_scores = {}
        for task_type, patterns in self.TASK_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += 1
            task_scores[task_type] = score
            
        # Get task with highest score
        if task_scores:
            detected_task = max(task_scores.items(), key=lambda x: x[1])
            if detected_task[1] > 0:
                task_type = detected_task[0]
            else:
                task_type = TaskType.GENERAL
        else:
            task_type = TaskType.GENERAL
            
        # Cache result
        self.task_cache[cache_key] = task_type
        
        return task_type
        
    def select_model(
        self,
        task_type: TaskType,
        available_models: List[str],
        preferences: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Select best model for task
        
        Args:
            task_type: Type of task
            available_models: List of available model names
            preferences: User preferences (cost_sensitive, quality_priority, speed_priority)
            
        Returns:
            Selected model name or None
        """
        if not available_models:
            return None
            
        preferences = preferences or {}
        cost_sensitive = preferences.get("cost_sensitive", True)
        quality_priority = preferences.get("quality_priority", False)
        speed_priority = preferences.get("speed_priority", False)
        prefer_local = preferences.get("prefer_local", True)
        
        # Filter models that support the task
        suitable_models = []
        for model in available_models:
            if model in self.MODEL_CAPABILITIES:
                capabilities = self.MODEL_CAPABILITIES[model]
                if task_type in capabilities.task_types:
                    suitable_models.append(model)
                    
        if not suitable_models:
            # Fallback to any available model
            suitable_models = available_models
            
        # Score models
        model_scores = {}
        for model in suitable_models:
            if model not in self.MODEL_CAPABILITIES:
                # Unknown model, give it a default score
                model_scores[model] = 5.0
                continue
                
            cap = self.MODEL_CAPABILITIES[model]
            score = 0.0
            
            # Base score from quality
            score += cap.quality_score * 2
            
            # Adjust for preferences
            if cost_sensitive:
                if cap.cost_per_1k_tokens == 0:
                    score += 5  # Big bonus for free models
                else:
                    score -= cap.cost_per_1k_tokens * 10
                    
            if quality_priority:
                score += cap.quality_score * 3
                
            if speed_priority:
                score += cap.speed_score * 2
                
            if prefer_local and cap.provider == "ollama":
                score += 3
                
            # Task-specific bonuses
            if task_type == TaskType.CODE and "code" in model.lower():
                score += 3
            elif task_type == TaskType.CREATIVE and cap.quality_score >= 8:
                score += 2
            elif task_type == TaskType.MATH and cap.quality_score >= 9:
                score += 3
                
            model_scores[model] = score
            
        # Select highest scoring model
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1])[0]
            return best_model
            
        return suitable_models[0] if suitable_models else None
        
    def get_fallback_models(self, primary_model: str) -> List[str]:
        """
        Get fallback models for a given primary model
        
        Args:
            primary_model: Primary model name
            
        Returns:
            List of fallback model names
        """
        fallbacks = []
        
        if primary_model in self.MODEL_CAPABILITIES:
            primary_cap = self.MODEL_CAPABILITIES[primary_model]
            
            # Find similar models
            for model, cap in self.MODEL_CAPABILITIES.items():
                if model != primary_model:
                    # Check if it supports similar tasks
                    common_tasks = set(primary_cap.task_types) & set(cap.task_types)
                    if len(common_tasks) >= len(primary_cap.task_types) * 0.5:
                        fallbacks.append(model)
                        
        # Sort fallbacks by quality
        fallbacks.sort(
            key=lambda m: self.MODEL_CAPABILITIES.get(m, ModelCapabilities("", "", [], 0, 0, 0, 0)).quality_score,
            reverse=True
        )
        
        return fallbacks[:3]  # Return top 3 fallbacks