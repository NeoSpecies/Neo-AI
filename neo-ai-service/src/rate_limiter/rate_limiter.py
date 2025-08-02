"""Rate limiter for AI Service"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

from .token_bucket import TokenBucket

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    enabled: bool = True
    
    # Global limits
    global_requests_per_second: float = 10
    global_requests_per_minute: float = 100
    global_burst_size: int = 20
    
    # Per-client limits
    client_requests_per_second: float = 2
    client_requests_per_minute: float = 20
    client_burst_size: int = 5
    
    # Model-specific limits (optional)
    model_limits: Dict[str, Dict[str, float]] = None
    
    # Priority levels
    enable_priority: bool = True
    high_priority_multiplier: float = 2.0  # High priority gets 2x rate


class RateLimiter:
    """Rate limiter for controlling request rates"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        
        # Global rate limiters
        self.global_second_bucket = TokenBucket(
            capacity=int(config.global_burst_size),
            refill_rate=config.global_requests_per_second
        )
        
        self.global_minute_bucket = TokenBucket(
            capacity=int(config.global_requests_per_minute),
            refill_rate=config.global_requests_per_minute / 60
        )
        
        # Per-client rate limiters
        self.client_second_buckets: Dict[str, TokenBucket] = {}
        self.client_minute_buckets: Dict[str, TokenBucket] = {}
        
        # Statistics
        self.total_requests = 0
        self.rejected_requests = 0
        self.client_stats = defaultdict(lambda: {"allowed": 0, "rejected": 0})
        
    async def check_rate_limit(
        self, 
        client_id: str, 
        model: str = None,
        priority: str = "normal",
        tokens: int = 1
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is allowed under rate limits
        
        Args:
            client_id: Client identifier
            model: Model being requested (for model-specific limits)
            priority: Request priority (normal, high)
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, wait_time_seconds)
        """
        if not self.config.enabled:
            return True, None
            
        self.total_requests += 1
        
        # Adjust tokens based on priority
        if self.config.enable_priority and priority == "high":
            effective_tokens = tokens / self.config.high_priority_multiplier
        else:
            effective_tokens = tokens
            
        # Check global limits
        if not await self.global_second_bucket.consume(effective_tokens):
            wait_time = await self.global_second_bucket.get_wait_time(effective_tokens)
            self._record_rejection(client_id, "global_second_limit")
            return False, wait_time
            
        if not await self.global_minute_bucket.consume(effective_tokens):
            wait_time = await self.global_minute_bucket.get_wait_time(effective_tokens)
            self._record_rejection(client_id, "global_minute_limit")
            return False, wait_time
            
        # Check client-specific limits
        client_second = self._get_client_bucket(client_id, "second")
        if not await client_second.consume(effective_tokens):
            wait_time = await client_second.get_wait_time(effective_tokens)
            self._record_rejection(client_id, "client_second_limit")
            return False, wait_time
            
        client_minute = self._get_client_bucket(client_id, "minute")
        if not await client_minute.consume(effective_tokens):
            wait_time = await client_minute.get_wait_time(effective_tokens)
            self._record_rejection(client_id, "client_minute_limit")
            return False, wait_time
            
        # Check model-specific limits if configured
        if model and self.config.model_limits and model in self.config.model_limits:
            model_limit = self.config.model_limits[model]
            # TODO: Implement model-specific rate limiting
            
        # Request allowed
        self.client_stats[client_id]["allowed"] += 1
        logger.debug(f"Rate limit passed for client {client_id} (priority: {priority})")
        return True, None
        
    async def wait_if_needed(
        self,
        client_id: str,
        model: str = None,
        priority: str = "normal",
        tokens: int = 1,
        max_wait: float = 60.0
    ) -> bool:
        """
        Wait for rate limit to allow request
        
        Args:
            client_id: Client identifier
            model: Model being requested
            priority: Request priority
            tokens: Number of tokens to consume
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if request allowed after waiting, False if timeout
        """
        start_time = time.time()
        
        while True:
            allowed, wait_time = await self.check_rate_limit(client_id, model, priority, tokens)
            
            if allowed:
                return True
                
            if wait_time is None or wait_time <= 0:
                wait_time = 0.1  # Default wait
                
            # Check if we've exceeded max wait time
            elapsed = time.time() - start_time
            if elapsed + wait_time > max_wait:
                return False
                
            logger.debug(f"Rate limited, waiting {wait_time:.2f}s for client {client_id}")
            await asyncio.sleep(min(wait_time, max_wait - elapsed))
            
    def _get_client_bucket(self, client_id: str, bucket_type: str) -> TokenBucket:
        """Get or create client-specific token bucket"""
        if bucket_type == "second":
            if client_id not in self.client_second_buckets:
                self.client_second_buckets[client_id] = TokenBucket(
                    capacity=self.config.client_burst_size,
                    refill_rate=self.config.client_requests_per_second
                )
            return self.client_second_buckets[client_id]
        else:  # minute
            if client_id not in self.client_minute_buckets:
                self.client_minute_buckets[client_id] = TokenBucket(
                    capacity=int(self.config.client_requests_per_minute),
                    refill_rate=self.config.client_requests_per_minute / 60
                )
            return self.client_minute_buckets[client_id]
            
    def _record_rejection(self, client_id: str, reason: str):
        """Record rejected request"""
        self.rejected_requests += 1
        self.client_stats[client_id]["rejected"] += 1
        logger.warning(f"Rate limit exceeded for client {client_id}: {reason}")
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        total_allowed = sum(stats["allowed"] for stats in self.client_stats.values())
        
        return {
            "enabled": self.config.enabled,
            "total_requests": self.total_requests,
            "allowed_requests": total_allowed,
            "rejected_requests": self.rejected_requests,
            "rejection_rate": self.rejected_requests / self.total_requests if self.total_requests > 0 else 0,
            "active_clients": len(self.client_stats),
            "global_tokens": {
                "second": await self.global_second_bucket.get_tokens(),
                "minute": await self.global_minute_bucket.get_tokens()
            },
            "limits": {
                "global_rps": self.config.global_requests_per_second,
                "global_rpm": self.config.global_requests_per_minute,
                "client_rps": self.config.client_requests_per_second,
                "client_rpm": self.config.client_requests_per_minute
            }
        }
        
    async def reset_client(self, client_id: str):
        """Reset rate limits for a specific client"""
        if client_id in self.client_second_buckets:
            del self.client_second_buckets[client_id]
        if client_id in self.client_minute_buckets:
            del self.client_minute_buckets[client_id]
        if client_id in self.client_stats:
            del self.client_stats[client_id]
            
    async def cleanup_inactive_clients(self, inactive_threshold: int = 3600):
        """Clean up inactive client buckets to save memory"""
        # TODO: Track last activity time and clean up inactive clients
        pass