"""Error handler with retry and fallback logic"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from functools import wraps

from .exceptions import AIServiceError, AdapterError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class ErrorConfig:
    """Error handling configuration"""
    enable_retry: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay in seconds
    retry_backoff: float = 2.0  # Exponential backoff multiplier
    
    enable_fallback: bool = True
    log_errors: bool = True
    
    # Circuit breaker settings
    enable_circuit_breaker: bool = True
    failure_threshold: int = 5
    recovery_timeout: int = 60  # Seconds
    
    # Error response formatting
    include_details: bool = False  # Include error details in response
    include_traceback: bool = False  # Include traceback (debug mode only)


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def record_success(self):
        """Record successful call"""
        self.failure_count = 0
        self.state = "closed"
        
    def record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
    def can_attempt(self) -> bool:
        """Check if we can attempt a call"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker moved to half-open state")
                return True
            return False
            
        # half-open state
        return True


class ErrorHandler:
    """Centralized error handling with retry and fallback"""
    
    def __init__(self, config: ErrorConfig):
        self.config = config
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_stats = {
            "total_errors": 0,
            "retries": 0,
            "fallbacks": 0,
            "circuit_breaker_trips": 0,
            "error_types": {}
        }
        
    def with_retry(self, func: Callable = None, *, service_name: str = None):
        """Decorator for automatic retry with exponential backoff"""
        def decorator(f):
            @wraps(f)
            async def wrapper(*args, **kwargs):
                last_error = None
                
                for attempt in range(self.config.max_retries + 1):
                    try:
                        # Check circuit breaker
                        if service_name and self.config.enable_circuit_breaker:
                            breaker = self._get_circuit_breaker(service_name)
                            if not breaker.can_attempt():
                                raise AIServiceError(
                                    f"Circuit breaker open for {service_name}",
                                    error_code="CIRCUIT_BREAKER_OPEN"
                                )
                                
                        # Attempt the call
                        result = await f(*args, **kwargs)
                        
                        # Record success
                        if service_name and self.config.enable_circuit_breaker:
                            breaker.record_success()
                            
                        return result
                        
                    except Exception as e:
                        last_error = e
                        self._record_error(e)
                        
                        # Record failure
                        if service_name and self.config.enable_circuit_breaker:
                            breaker = self._get_circuit_breaker(service_name)
                            breaker.record_failure()
                            
                        # Don't retry certain errors
                        if isinstance(e, (ValidationError, RateLimitError)):
                            raise
                            
                        # Check if we should retry
                        if attempt < self.config.max_retries and self.config.enable_retry:
                            delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                            logger.warning(
                                f"Retry {attempt + 1}/{self.config.max_retries} "
                                f"after {delay:.1f}s for: {str(e)}"
                            )
                            self.error_stats["retries"] += 1
                            await asyncio.sleep(delay)
                        else:
                            raise
                            
                # All retries failed
                raise last_error
                
            return wrapper
        return decorator if func is None else decorator(func)
        
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        fallback_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle error with logging and optional fallback
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            fallback_func: Optional fallback function to call
            
        Returns:
            Error response dictionary
        """
        self._record_error(error)
        
        # Log error
        if self.config.log_errors:
            logger.error(
                f"Error in AI Service: {str(error)}",
                exc_info=self.config.include_traceback,
                extra={"context": context}
            )
            
        # Try fallback
        if fallback_func and self.config.enable_fallback:
            try:
                logger.info("Attempting fallback...")
                self.error_stats["fallbacks"] += 1
                return await fallback_func()
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                error = fallback_error
                
        # Format error response
        return self._format_error_response(error, context)
        
    def _record_error(self, error: Exception):
        """Record error statistics"""
        self.error_stats["total_errors"] += 1
        
        error_type = type(error).__name__
        if error_type not in self.error_stats["error_types"]:
            self.error_stats["error_types"][error_type] = 0
        self.error_stats["error_types"][error_type] += 1
        
    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                self.config.failure_threshold,
                self.config.recovery_timeout
            )
        return self.circuit_breakers[service_name]
        
    def _format_error_response(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format error into response dictionary"""
        response = {
            "status": "error",
            "error": str(error)
        }
        
        # Add error code if available
        if isinstance(error, AIServiceError) and error.error_code:
            response["error_code"] = error.error_code
            
        # Add details if configured
        if self.config.include_details:
            response["details"] = {}
            
            if isinstance(error, AIServiceError) and error.details:
                response["details"].update(error.details)
                
            if context:
                response["details"]["context"] = context
                
            # Add retry information
            if isinstance(error, RateLimitError) and error.details.get("wait_time"):
                response["retry_after"] = error.details["wait_time"]
                
        return response
        
    def get_stats(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        return {
            "total_errors": self.error_stats["total_errors"],
            "retries": self.error_stats["retries"],
            "fallbacks": self.error_stats["fallbacks"],
            "circuit_breakers": {
                name: {
                    "state": breaker.state,
                    "failures": breaker.failure_count
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "error_types": self.error_stats["error_types"]
        }
        
    def reset_stats(self):
        """Reset error statistics"""
        self.error_stats = {
            "total_errors": 0,
            "retries": 0,
            "fallbacks": 0,
            "circuit_breaker_trips": 0,
            "error_types": {}
        }


# Import ValidationError after definition to avoid circular import
from .exceptions import ValidationError