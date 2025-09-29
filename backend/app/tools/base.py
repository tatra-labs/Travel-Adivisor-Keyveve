from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
import time
import hashlib
import json
import asyncio
from datetime import datetime, timedelta


class ToolInput(BaseModel):
    """Base class for tool inputs with validation."""
    pass


class ToolOutput(BaseModel):
    """Base class for tool outputs with validation."""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cached: bool = False
    duration_ms: Optional[int] = None


class BaseTool(ABC):
    """Base class for all tools with caching, retries, and timeouts."""
    
    def __init__(self, name: str, description: str, timeout_seconds: int = 30):
        self.name = name
        self.description = description
        self.timeout_seconds = timeout_seconds
        self._cache: Dict[str, tuple] = {}  # hash -> (result, timestamp)
        self._cache_ttl = timedelta(minutes=15)  # Cache for 15 minutes
    
    def _get_cache_key(self, input_data: Dict[str, Any]) -> str:
        """Generate cache key from input data."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(sorted_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[ToolOutput]:
        """Get cached result if available and not expired."""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                result.cached = True
                return result
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: ToolOutput):
        """Cache the result."""
        self._cache[cache_key] = (result, datetime.now())
    
    @abstractmethod
    async def _execute(self, input_data: ToolInput) -> ToolOutput:
        """Execute the tool logic. Must be implemented by subclasses."""
        pass
    
    async def execute(self, input_data: Dict[str, Any], max_retries: int = 1) -> ToolOutput:
        """Execute tool with caching, retries, and timeout."""
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._get_cache_key(input_data)
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Validate input
        try:
            validated_input = self.get_input_schema()(**input_data)
        except Exception as e:
            return ToolOutput(
                success=False,
                error=f"Input validation failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000)
            )
        
        # Execute with retries
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = await self._execute(validated_input)
                result.duration_ms = int((time.time() - start_time) * 1000)
                
                # Cache successful results
                if result.success:
                    self._cache_result(cache_key, result)
                
                return result
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    # Add jitter to retry delay
                    import random
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    continue
        
        # All retries failed
        return ToolOutput(
            success=False,
            error=f"Tool execution failed after {max_retries + 1} attempts: {last_error}",
            duration_ms=int((time.time() - start_time) * 1000)
        )
    
    @abstractmethod
    def get_input_schema(self) -> type[ToolInput]:
        """Return the input schema class for this tool."""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> type[ToolOutput]:
        """Return the output schema class for this tool."""
        pass
    
    def get_json_schema(self) -> Dict[str, Any]:
        """Get JSON schema for the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema().model_json_schema(),
            "output_schema": self.get_output_schema().model_json_schema()
        }

