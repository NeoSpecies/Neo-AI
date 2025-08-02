"""Cache manager for AI Service"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import OrderedDict
import aiofiles
import os

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool = True
    max_size: int = 1000  # Maximum number of entries
    ttl_seconds: int = 3600  # 1 hour default TTL
    storage_type: str = "memory"  # memory, file, redis (future)
    storage_path: str = "cache"  # For file-based cache
    
    
@dataclass
class CacheEntry:
    """A single cache entry"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: int = 3600
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() - self.created_at > self.ttl
        
    def touch(self):
        """Update access time and count"""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheManager:
    """Manages caching for AI responses"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Create cache directory for file storage
        if config.storage_type == "file" and config.enabled:
            os.makedirs(config.storage_path, exist_ok=True)
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.config.enabled:
            return None
            
        entry = self.cache.get(key)
        if entry is None:
            self.misses += 1
            # Try to load from file if using file storage
            if self.config.storage_type == "file":
                entry = await self._load_from_file(key)
                if entry:
                    self.cache[key] = entry
                else:
                    return None
            else:
                return None
                
        # Check expiration
        if entry.is_expired():
            await self.delete(key)
            self.misses += 1
            return None
            
        # Update access info
        entry.touch()
        self.hits += 1
        
        # Move to end (LRU)
        self.cache.move_to_end(key)
        
        logger.debug(f"Cache hit for key: {key[:8]}... (hits: {self.hits}, misses: {self.misses})")
        return entry.value
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if not self.config.enabled:
            return
            
        # Check size limit
        if len(self.cache) >= self.config.max_size:
            await self._evict_lru()
            
        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            accessed_at=time.time(),
            ttl=ttl or self.config.ttl_seconds
        )
        
        self.cache[key] = entry
        
        # Save to file if using file storage
        if self.config.storage_type == "file":
            await self._save_to_file(key, entry)
            
        logger.debug(f"Cached response for key: {key[:8]}... (size: {len(self.cache)})")
        
    async def delete(self, key: str) -> None:
        """Delete entry from cache"""
        if key in self.cache:
            del self.cache[key]
            
        # Delete file if using file storage
        if self.config.storage_type == "file":
            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)
                
    async def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Clear files if using file storage
        if self.config.storage_type == "file":
            for file in os.listdir(self.config.storage_path):
                if file.endswith('.json'):
                    os.remove(os.path.join(self.config.storage_path, file))
                    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "enabled": self.config.enabled,
            "size": len(self.cache),
            "max_size": self.config.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "storage_type": self.config.storage_type
        }
        
    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self.cache:
            # Remove first item (least recently used)
            key, entry = self.cache.popitem(last=False)
            self.evictions += 1
            
            # Delete file if using file storage
            if self.config.storage_type == "file":
                file_path = self._get_file_path(key)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
            logger.debug(f"Evicted cache entry: {key[:8]}...")
            
    def _get_file_path(self, key: str) -> str:
        """Get file path for cache entry"""
        return os.path.join(self.config.storage_path, f"{key}.json")
        
    async def _save_to_file(self, key: str, entry: CacheEntry) -> None:
        """Save cache entry to file"""
        try:
            file_path = self._get_file_path(key)
            data = {
                'key': entry.key,
                'value': entry.value,
                'created_at': entry.created_at,
                'accessed_at': entry.accessed_at,
                'access_count': entry.access_count,
                'ttl': entry.ttl
            }
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(data))
                
        except Exception as e:
            logger.error(f"Failed to save cache to file: {e}")
            
    async def _load_from_file(self, key: str) -> Optional[CacheEntry]:
        """Load cache entry from file"""
        try:
            file_path = self._get_file_path(key)
            if not os.path.exists(file_path):
                return None
                
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
                
            entry = CacheEntry(
                key=data['key'],
                value=data['value'],
                created_at=data['created_at'],
                accessed_at=data['accessed_at'],
                access_count=data.get('access_count', 0),
                ttl=data.get('ttl', self.config.ttl_seconds)
            )
            
            return entry if not entry.is_expired() else None
            
        except Exception as e:
            logger.error(f"Failed to load cache from file: {e}")
            return None
            
    async def cleanup_expired(self) -> int:
        """Remove expired entries"""
        expired_keys = []
        for key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
                
        for key in expired_keys:
            await self.delete(key)
            
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        return len(expired_keys)