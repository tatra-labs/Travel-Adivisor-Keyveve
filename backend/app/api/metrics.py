from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime
import time
import threading
from collections import defaultdict, deque
from app.auth.rate_limiter import rate_limiter

router = APIRouter()

# Global metrics storage
class MetricsCollector:
    """Thread-safe metrics collector."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._node_timings = defaultdict(list)  # node_name -> [duration_ms, ...]
        self._tool_calls = defaultdict(int)     # tool_name -> count
        self._tool_errors = defaultdict(int)    # tool_name -> error_count
        self._cache_hits = 0
        self._cache_misses = 0
        self._agent_runs = 0
        self._start_time = time.time()
        
        # Keep only recent data (last 1000 entries per metric)
        self._max_entries = 1000
    
    def record_node_timing(self, node_name: str, duration_ms: int):
        """Record timing for a graph node."""
        with self._lock:
            timings = self._node_timings[node_name]
            timings.append(duration_ms)
            if len(timings) > self._max_entries:
                timings.pop(0)
    
    def record_tool_call(self, tool_name: str, success: bool, cached: bool = False):
        """Record a tool call."""
        with self._lock:
            self._tool_calls[tool_name] += 1
            if not success:
                self._tool_errors[tool_name] += 1
            if cached:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
    
    def record_agent_run(self):
        """Record an agent run."""
        with self._lock:
            self._agent_runs += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            
            # Calculate node timing statistics
            node_stats = {}
            for node_name, timings in self._node_timings.items():
                if timings:
                    node_stats[node_name] = {
                        "count": len(timings),
                        "avg_ms": sum(timings) / len(timings),
                        "min_ms": min(timings),
                        "max_ms": max(timings),
                        "p95_ms": self._percentile(timings, 95),
                        "p99_ms": self._percentile(timings, 99)
                    }
            
            # Calculate cache hit rate
            total_cache_requests = self._cache_hits + self._cache_misses
            cache_hit_rate = (self._cache_hits / total_cache_requests) if total_cache_requests > 0 else 0
            
            # Calculate tool error rates
            tool_error_rates = {}
            for tool_name in self._tool_calls:
                total_calls = self._tool_calls[tool_name]
                errors = self._tool_errors[tool_name]
                tool_error_rates[tool_name] = {
                    "total_calls": total_calls,
                    "errors": errors,
                    "error_rate": errors / total_calls if total_calls > 0 else 0
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": uptime_seconds,
                "agent_runs": self._agent_runs,
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": cache_hit_rate
                },
                "node_timings": node_stats,
                "tool_stats": tool_error_rates,
                "rate_limiter": rate_limiter.get_stats()
            }
    
    def _percentile(self, data: list, percentile: int) -> float:
        """Calculate percentile of a list."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


# Global metrics collector instance
metrics_collector = MetricsCollector()


@router.get("/metrics")
async def get_metrics():
    """
    Get application metrics in JSON format.
    Includes node timings, cache hit rates, tool error counts, etc.
    """
    return metrics_collector.get_metrics()


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format.
    """
    metrics = metrics_collector.get_metrics()
    
    # Convert to Prometheus format
    prometheus_lines = [
        "# HELP travel_agent_uptime_seconds Application uptime in seconds",
        "# TYPE travel_agent_uptime_seconds counter",
        f"travel_agent_uptime_seconds {metrics['uptime_seconds']}",
        "",
        "# HELP travel_agent_runs_total Total number of agent runs",
        "# TYPE travel_agent_runs_total counter", 
        f"travel_agent_runs_total {metrics['agent_runs']}",
        "",
        "# HELP travel_agent_cache_hit_rate Cache hit rate",
        "# TYPE travel_agent_cache_hit_rate gauge",
        f"travel_agent_cache_hit_rate {metrics['cache']['hit_rate']}",
        "",
        "# HELP travel_agent_cache_operations_total Total cache operations",
        "# TYPE travel_agent_cache_operations_total counter",
        f"travel_agent_cache_operations_total{{type=\"hit\"}} {metrics['cache']['hits']}",
        f"travel_agent_cache_operations_total{{type=\"miss\"}} {metrics['cache']['misses']}",
        ""
    ]
    
    # Add node timing metrics
    prometheus_lines.extend([
        "# HELP travel_agent_node_duration_ms Node execution duration in milliseconds",
        "# TYPE travel_agent_node_duration_ms histogram"
    ])
    
    for node_name, stats in metrics['node_timings'].items():
        prometheus_lines.extend([
            f"travel_agent_node_duration_ms_count{{node=\"{node_name}\"}} {stats['count']}",
            f"travel_agent_node_duration_ms_sum{{node=\"{node_name}\"}} {stats['avg_ms'] * stats['count']}",
            f"travel_agent_node_duration_ms_bucket{{node=\"{node_name}\",le=\"100\"}} {stats['count']}",  # Simplified
        ])
    
    prometheus_lines.append("")
    
    # Add tool error metrics
    prometheus_lines.extend([
        "# HELP travel_agent_tool_calls_total Total tool calls",
        "# TYPE travel_agent_tool_calls_total counter",
        "# HELP travel_agent_tool_errors_total Total tool errors", 
        "# TYPE travel_agent_tool_errors_total counter"
    ])
    
    for tool_name, stats in metrics['tool_stats'].items():
        prometheus_lines.extend([
            f"travel_agent_tool_calls_total{{tool=\"{tool_name}\"}} {stats['total_calls']}",
            f"travel_agent_tool_errors_total{{tool=\"{tool_name}\"}} {stats['errors']}"
        ])
    
    return "\n".join(prometheus_lines)

