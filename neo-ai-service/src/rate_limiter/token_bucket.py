"""Token bucket algorithm implementation"""

import time
import asyncio
from typing import Optional


class TokenBucket:
    """
    Token bucket algorithm for rate limiting
    
    Tokens are added at a constant rate up to a maximum capacity.
    Each request consumes tokens.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        async with self._lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
            
    async def consume_with_wait(self, tokens: int = 1, max_wait: float = None) -> bool:
        """
        Try to consume tokens, wait if necessary
        
        Args:
            tokens: Number of tokens to consume
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if tokens were consumed, False if timeout
        """
        start_time = time.time()
        
        while True:
            if await self.consume(tokens):
                return True
                
            # Check timeout
            if max_wait is not None:
                elapsed = time.time() - start_time
                if elapsed >= max_wait:
                    return False
                    
            # Calculate wait time
            async with self._lock:
                await self._refill()
                if self.tokens < tokens:
                    needed = tokens - self.tokens
                    wait_time = needed / self.refill_rate
                    
                    # Adjust for max_wait
                    if max_wait is not None:
                        remaining = max_wait - (time.time() - start_time)
                        wait_time = min(wait_time, remaining)
                        
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                        
    async def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
    async def get_tokens(self) -> float:
        """Get current number of tokens"""
        async with self._lock:
            await self._refill()
            return self.tokens
            
    async def get_wait_time(self, tokens: int = 1) -> Optional[float]:
        """
        Get estimated wait time for tokens to be available
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds, or None if tokens available now
        """
        async with self._lock:
            await self._refill()
            
            if self.tokens >= tokens:
                return None
                
            needed = tokens - self.tokens
            return needed / self.refill_rate