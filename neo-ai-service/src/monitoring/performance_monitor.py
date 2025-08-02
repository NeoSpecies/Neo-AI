"""Performance monitoring for AI Service"""

import asyncio
import psutil
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class MonitorConfig:
    """Performance monitor configuration"""
    enabled: bool = True
    
    # Collection intervals
    system_metrics_interval: int = 10  # seconds
    service_metrics_interval: int = 5  # seconds
    cleanup_interval: int = 300  # seconds
    
    # Metric settings
    enable_system_metrics: bool = True
    enable_service_metrics: bool = True
    enable_model_metrics: bool = True
    enable_cache_metrics: bool = True
    enable_rate_limit_metrics: bool = True
    
    # Export settings
    export_format: str = "json"  # json, prometheus
    export_path: Optional[str] = None
    export_interval: int = 60  # seconds
    
    # Alerting thresholds
    cpu_threshold: float = 80.0  # percentage
    memory_threshold: float = 80.0  # percentage
    error_rate_threshold: float = 5.0  # percentage
    latency_threshold: float = 2.0  # seconds


class PerformanceMonitor:
    """Monitors system and service performance"""
    
    def __init__(self, config: MonitorConfig):
        self.config = config
        self.collector = MetricsCollector()
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Component references (set later)
        self.cache_manager = None
        self.rate_limiter = None
        self.model_router = None
        self.error_handler = None
        
        # Alert state
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        
    def set_components(self, **components):
        """Set references to monitored components"""
        self.cache_manager = components.get('cache_manager')
        self.rate_limiter = components.get('rate_limiter')
        self.model_router = components.get('model_router')
        self.error_handler = components.get('error_handler')
        
    async def start(self):
        """Start monitoring tasks"""
        if not self.config.enabled:
            logger.info("Performance monitoring disabled")
            return
            
        self.running = True
        
        # Start collection tasks
        if self.config.enable_system_metrics:
            self.tasks.append(
                asyncio.create_task(self._collect_system_metrics())
            )
            
        if self.config.enable_service_metrics:
            self.tasks.append(
                asyncio.create_task(self._collect_service_metrics())
            )
            
        # Start cleanup task
        self.tasks.append(
            asyncio.create_task(self._cleanup_task())
        )
        
        # Start export task
        if self.config.export_path:
            self.tasks.append(
                asyncio.create_task(self._export_task())
            )
            
        logger.info("Performance monitoring started")
        
    async def stop(self):
        """Stop monitoring tasks"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        logger.info("Performance monitoring stopped")
        
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        while self.running:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                self.collector.record_gauge("system.cpu.percent", cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.collector.record_gauge("system.memory.percent", memory.percent)
                self.collector.record_gauge("system.memory.used_gb", memory.used / (1024**3))
                self.collector.record_gauge("system.memory.available_gb", memory.available / (1024**3))
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                self.collector.record_gauge("system.disk.percent", disk.percent)
                self.collector.record_gauge("system.disk.used_gb", disk.used / (1024**3))
                
                # Network metrics (if available)
                try:
                    net_io = psutil.net_io_counters()
                    self.collector.record_counter("system.network.bytes_sent", net_io.bytes_sent)
                    self.collector.record_counter("system.network.bytes_recv", net_io.bytes_recv)
                except:
                    pass
                    
                # Check alerts
                self._check_system_alerts(cpu_percent, memory.percent)
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                
            await asyncio.sleep(self.config.system_metrics_interval)
            
    async def _collect_service_metrics(self):
        """Collect service-level metrics"""
        while self.running:
            try:
                # Cache metrics
                if self.config.enable_cache_metrics and self.cache_manager:
                    cache_stats = self.cache_manager.get_stats()
                    self.collector.record_gauge("cache.size", cache_stats['total_items'])
                    self.collector.record_gauge("cache.memory_mb", cache_stats['memory_usage'] / (1024**2))
                    self.collector.record_gauge("cache.hit_rate", cache_stats['hit_rate'])
                    self.collector.record_counter("cache.hits", cache_stats['hits'])
                    self.collector.record_counter("cache.misses", cache_stats['misses'])
                    
                # Rate limiter metrics
                if self.config.enable_rate_limit_metrics and self.rate_limiter:
                    rl_stats = self.rate_limiter.get_stats()
                    self.collector.record_counter("rate_limit.allowed", rl_stats['total_allowed'])
                    self.collector.record_counter("rate_limit.denied", rl_stats['total_denied'])
                    self.collector.record_gauge("rate_limit.active_clients", len(rl_stats['client_stats']))
                    
                # Model router metrics
                if self.config.enable_model_metrics and self.model_router:
                    router_stats = self.model_router.get_stats()
                    self.collector.record_counter("router.requests", router_stats['total_requests'])
                    self.collector.record_counter("router.fallbacks", router_stats['fallback_used'])
                    self.collector.record_counter("router.failures", router_stats['failed_routing'])
                    
                    # Per-model metrics
                    for model_stat in router_stats.get('model_health', []):
                        tags = {"model": model_stat['model']}
                        self.collector.record_gauge(
                            "model.success_rate", 
                            model_stat['success_rate'],
                            tags=tags
                        )
                        self.collector.record_gauge(
                            "model.avg_response_time",
                            model_stat['avg_response_time'],
                            tags=tags
                        )
                        
                # Error handler metrics
                if self.error_handler:
                    error_stats = self.error_handler.get_stats()
                    self.collector.record_counter("errors.total", error_stats['total_errors'])
                    self.collector.record_counter("errors.retries", error_stats['retries'])
                    self.collector.record_counter("errors.fallbacks", error_stats['fallbacks'])
                    
                    # Per-error-type metrics
                    for error_type, count in error_stats['error_types'].items():
                        self.collector.record_counter(
                            "errors.by_type",
                            count,
                            tags={"type": error_type}
                        )
                        
            except Exception as e:
                logger.error(f"Error collecting service metrics: {e}")
                
            await asyncio.sleep(self.config.service_metrics_interval)
            
    async def _cleanup_task(self):
        """Periodically clean up old metrics"""
        while self.running:
            try:
                self.collector.clear_old_metrics()
                logger.debug("Cleaned up old metrics")
            except Exception as e:
                logger.error(f"Error during metric cleanup: {e}")
                
            await asyncio.sleep(self.config.cleanup_interval)
            
    async def _export_task(self):
        """Export metrics to file"""
        while self.running:
            try:
                await self.export_metrics()
            except Exception as e:
                logger.error(f"Error exporting metrics: {e}")
                
            await asyncio.sleep(self.config.export_interval)
            
    async def export_metrics(self):
        """Export current metrics"""
        if not self.config.export_path:
            return
            
        summaries = self.collector.get_all_summaries()
        
        if self.config.export_format == "json":
            # Export as JSON
            export_data = {
                "timestamp": time.time(),
                "metrics": {
                    name: {
                        "count": summary.count,
                        "sum": summary.sum,
                        "min": summary.min,
                        "max": summary.max,
                        "mean": summary.mean,
                        "median": summary.median,
                        "p95": summary.p95,
                        "p99": summary.p99
                    }
                    for name, summary in summaries.items()
                },
                "alerts": self.active_alerts
            }
            
            with open(self.config.export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
        elif self.config.export_format == "prometheus":
            # Export in Prometheus format
            lines = []
            for name, summary in summaries.items():
                safe_name = name.replace(".", "_").replace("-", "_")
                lines.append(f"# TYPE {safe_name} summary")
                lines.append(f"{safe_name}_count {summary.count}")
                lines.append(f"{safe_name}_sum {summary.sum}")
                lines.append(f"{safe_name}_min {summary.min}")
                lines.append(f"{safe_name}_max {summary.max}")
                lines.append(f"{safe_name}_mean {summary.mean}")
                lines.append(f"{safe_name}_p95 {summary.p95}")
                lines.append(f"{safe_name}_p99 {summary.p99}")
                lines.append("")
                
            with open(self.config.export_path, 'w') as f:
                f.write("\n".join(lines))
                
        logger.debug(f"Exported metrics to {self.config.export_path}")
        
    def record_request(self, endpoint: str, method: str, status: int, duration: float):
        """Record HTTP request metrics"""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status": str(status)
        }
        
        self.collector.record_counter("http.requests", tags=tags)
        self.collector.record_timer("http.request_duration", duration, tags=tags)
        
        if status >= 400:
            self.collector.record_counter("http.errors", tags=tags)
            
    def record_model_request(self, model: str, adapter: str, success: bool, duration: float):
        """Record model request metrics"""
        tags = {
            "model": model,
            "adapter": adapter,
            "success": str(success)
        }
        
        self.collector.record_counter("model.requests", tags=tags)
        self.collector.record_timer("model.request_duration", duration, tags=tags)
        
        if not success:
            self.collector.record_counter("model.errors", tags=tags)
            
    def _check_system_alerts(self, cpu_percent: float, memory_percent: float):
        """Check and manage system alerts"""
        # CPU alert
        if cpu_percent > self.config.cpu_threshold:
            self.active_alerts["high_cpu"] = {
                "message": f"CPU usage is {cpu_percent:.1f}%",
                "threshold": self.config.cpu_threshold,
                "current": cpu_percent,
                "timestamp": time.time()
            }
        elif "high_cpu" in self.active_alerts:
            del self.active_alerts["high_cpu"]
            
        # Memory alert
        if memory_percent > self.config.memory_threshold:
            self.active_alerts["high_memory"] = {
                "message": f"Memory usage is {memory_percent:.1f}%",
                "threshold": self.config.memory_threshold,
                "current": memory_percent,
                "timestamp": time.time()
            }
        elif "high_memory" in self.active_alerts:
            del self.active_alerts["high_memory"]
            
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        summaries = self.collector.get_all_summaries()
        
        return {
            "timestamp": time.time(),
            "system": {
                "cpu_percent": summaries.get("system.cpu.percent_current", {}).get("mean", 0),
                "memory_percent": summaries.get("system.memory.percent_current", {}).get("mean", 0),
                "disk_percent": summaries.get("system.disk.percent_current", {}).get("mean", 0)
            },
            "service": {
                "total_requests": summaries.get("http.requests_total", {}).get("sum", 0),
                "error_rate": self._calculate_error_rate(summaries),
                "avg_latency": summaries.get("http.request_duration", {}).get("mean", 0),
                "p95_latency": summaries.get("http.request_duration", {}).get("p95", 0)
            },
            "cache": {
                "hit_rate": summaries.get("cache.hit_rate_current", {}).get("mean", 0),
                "size": summaries.get("cache.size_current", {}).get("mean", 0)
            },
            "models": self._get_model_summary(summaries),
            "alerts": list(self.active_alerts.values())
        }
        
    def _calculate_error_rate(self, summaries: Dict[str, Any]) -> float:
        """Calculate error rate percentage"""
        total_requests = summaries.get("http.requests_total", {}).get("sum", 0)
        total_errors = summaries.get("http.errors_total", {}).get("sum", 0)
        
        if total_requests > 0:
            return (total_errors / total_requests) * 100
        return 0
        
    def _get_model_summary(self, summaries: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get per-model performance summary"""
        model_summary = []
        
        # Extract model-specific metrics
        for name, summary in summaries.items():
            if name.startswith("model.") and "tags" in summary:
                model_name = summary["tags"].get("model")
                if model_name:
                    model_summary.append({
                        "model": model_name,
                        "metric": name.replace("model.", ""),
                        "value": summary["mean"]
                    })
                    
        return model_summary