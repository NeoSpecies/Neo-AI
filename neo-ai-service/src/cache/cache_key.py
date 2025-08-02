"""Cache key generation utilities"""

import hashlib
import json
from typing import List, Dict, Any


def generate_cache_key(model: str, messages: List[Dict[str, Any]], **kwargs) -> str:
    """
    Generate a unique cache key based on model and messages
    
    Args:
        model: Model name
        messages: List of message dictionaries
        **kwargs: Additional parameters that affect the response
        
    Returns:
        A unique cache key string
    """
    # Create a dictionary with all relevant parameters
    cache_data = {
        'model': model,
        'messages': messages,
        # Include parameters that affect the output
        'temperature': kwargs.get('temperature', 0.7),
        'max_tokens': kwargs.get('max_tokens'),
        'top_p': kwargs.get('top_p'),
    }
    
    # Convert to stable JSON string (sorted keys)
    cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=True)
    
    # Generate SHA256 hash
    return hashlib.sha256(cache_str.encode()).hexdigest()


def generate_semantic_key(messages: List[Dict[str, Any]]) -> str:
    """
    Generate a semantic key based on message content only
    Used for similar query matching
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        A semantic cache key
    """
    # Extract only the content from messages
    contents = []
    for msg in messages:
        if isinstance(msg, dict) and 'content' in msg:
            contents.append(msg['content'].lower().strip())
    
    content_str = ' '.join(contents)
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]  # Shorter key for grouping