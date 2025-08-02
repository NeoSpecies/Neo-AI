"""Metrics collection and aggregation"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class Metric:
    """Single metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    
@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    name: str
    count: int
    sum: float
    min: float
    max: float
    mean: float
    median: float
    p95: float
    p99: float
    tags: Dict[str, str] = field(default_factory=dict)

class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, window_size: int = 300, max_samples: int = 1000):
        """
        Initialize metrics collector
        
        Args:
            window_size: Time window in seconds for aggregation
            max_samples: Maximum samples to keep per metric
        """
        self.window_size = window_size
        self.max_samples = max_samples
        
        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        
        # Aggregated stats
        self.summaries: Dict[str, MetricSummary] = {}
        self.last_aggregation = time.time()
        
    def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Record counter metric (cumulative)"""
        metric = Metric(name, MetricType.COUNTER, value, tags=tags or {})
        self.counters[self._metric_key(name, tags)] += value
        self.metrics[name].append(metric)
        
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record gauge metric (current value)"""
        metric = Metric(name, MetricType.GAUGE, value, tags=tags or {})
        self.gauges[self._metric_key(name, tags)] = value
        self.metrics[name].append(metric)
        
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record histogram metric (distribution)"""
        metric = Metric(name, MetricType.HISTOGRAM, value, tags=tags or {})
        self.metrics[name].append(metric)
        
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record timer metric (duration in seconds)"""
        metric = Metric(name, MetricType.TIMER, duration, tags=tags or {})
        self.metrics[name].append(metric)
        
    def timer(self, name: str, tags: Dict[str, str] = None):
        """Context manager for timing operations"""
        class Timer:
            def __init__(self, collector, metric_name, metric_tags):
                self.collector = collector
                self.name = metric_name
                self.tags = metric_tags
                self.start_time = None
                
            def __enter__(self):
                self.start_time = time.time()
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.collector.record_timer(self.name, duration, self.tags)
                
        return Timer(self, name, tags)
        
    async def timer_async(self, name: str, tags: Dict[str, str] = None):
        """Async context manager for timing operations"""
        class AsyncTimer:
            def __init__(self, collector, metric_name, metric_tags):
                self.collector = collector
                self.name = metric_name
                self.tags = metric_tags
                self.start_time = None
                
            async def __aenter__(self):
                self.start_time = time.time()
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.collector.record_timer(self.name, duration, self.tags)
                
        return AsyncTimer(self, name, tags)
        
    def get_metric_summary(self, name: str, tags: Dict[str, str] = None) -> Optional[MetricSummary]:
        """Get summary statistics for a metric"""
        # Filter metrics by time window
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Get metrics within window
        recent_metrics = [
            m for m in self.metrics.get(name, [])
            if m.timestamp >= window_start and self._tags_match(m.tags, tags)
        ]
        
        if not recent_metrics:
            return None
            
        values = [m.value for m in recent_metrics]
        values.sort()
        
        return MetricSummary(
            name=name,
            count=len(values),
            sum=sum(values),
            min=min(values),
            max=max(values),
            mean=statistics.mean(values),
            median=statistics.median(values),
            p95=self._percentile(values, 0.95),
            p99=self._percentile(values, 0.99),
            tags=tags or {}
        )
        
    def get_all_summaries(self) -> Dict[str, MetricSummary]:
        """Get summaries for all metrics"""
        summaries = {}
        
        # Process all metrics
        for name in self.metrics:
            summary = self.get_metric_summary(name)
            if summary:
                summaries[name] = summary
                
        # Add counters
        for key, value in self.counters.items():
            name = key.split(":")[0]
            summaries[f"{name}_total"] = MetricSummary(
                name=f"{name}_total",
                count=1,
                sum=value,
                min=value,
                max=value,
                mean=value,
                median=value,
                p95=value,
                p99=value
            )
            
        # Add gauges
        for key, value in self.gauges.items():
            name = key.split(":")[0]
            summaries[f"{name}_current"] = MetricSummary(
                name=f"{name}_current",
                count=1,
                sum=value,
                min=value,
                max=value,
                mean=value,
                median=value,
                p95=value,
                p99=value
            )
            
        return summaries
        
    def clear_old_metrics(self):
        """Remove metrics outside the time window"""
        current_time = time.time()
        window_start = current_time - self.window_size
        
        for name in list(self.metrics.keys()):
            # Keep only recent metrics
            self.metrics[name] = deque(
                (m for m in self.metrics[name] if m.timestamp >= window_start),
                maxlen=self.max_samples
            )
            
            # Remove empty entries
            if not self.metrics[name]:
                del self.metrics[name]
                
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.summaries.clear()
        
    def _metric_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Generate unique key for metric with tags"""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}:{tag_str}"
        
    def _tags_match(self, metric_tags: Dict[str, str], filter_tags: Optional[Dict[str, str]]) -> bool:
        """Check if metric tags match filter"""
        if not filter_tags:
            return True
        return all(metric_tags.get(k) == v for k, v in filter_tags.items())
        
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0
        index = int(len(sorted_values) * percentile)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return sorted_values[index]