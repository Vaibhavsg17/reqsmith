"""
Performance metrics collection and monitoring for ReqSmith.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .logging_config import get_performance_logger


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    count: int
    sum: float
    min: float
    max: float
    avg: float
    p95: float
    p99: float


class MetricsCollector:
    """Thread-safe metrics collector."""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric."""
        with self.lock:
            point = MetricPoint(time.time(), duration, tags or {})
            self.metrics[f"timing.{name}"].append(point)
            
            # Also log to performance logger
            logger = get_performance_logger()
            logger.logger.debug(
                f"Timing metric: {name}",
                extra={
                    "metric_type": "timing",
                    "metric_name": name,
                    "duration_ms": duration * 1000,
                    "tags": tags or {}
                }
            )
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self.lock:
            key = f"counter.{name}"
            self.counters[key] += value
            
            # Record as a point for time-series analysis
            point = MetricPoint(time.time(), value, tags or {})
            self.metrics[key].append(point)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self.lock:
            key = f"gauge.{name}"
            self.gauges[key] = value
            
            # Record as a point for time-series analysis
            point = MetricPoint(time.time(), value, tags or {})
            self.metrics[key].append(point)
    
    def get_metric_summary(self, name: str, since: Optional[datetime] = None) -> Optional[MetricSummary]:
        """Get summary statistics for a metric."""
        with self.lock:
            if name not in self.metrics:
                return None
            
            points = list(self.metrics[name])
            if not points:
                return None
            
            # Filter by time if specified
            if since:
                since_timestamp = since.timestamp()
                points = [p for p in points if p.timestamp >= since_timestamp]
            
            if not points:
                return None
            
            values = [p.value for p in points]
            values.sort()
            
            count = len(values)
            total = sum(values)
            
            # Calculate percentiles
            p95_idx = int(count * 0.95)
            p99_idx = int(count * 0.99)
            
            return MetricSummary(
                count=count,
                sum=total,
                min=values[0],
                max=values[-1],
                avg=total / count,
                p95=values[p95_idx] if p95_idx < count else values[-1],
                p99=values[p99_idx] if p99_idx < count else values[-1]
            )
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics data."""
        with self.lock:
            now = time.time()
            uptime = now - self.start_time
            
            # Get summaries for all timing metrics
            timing_summaries = {}
            for name in self.metrics:
                if name.startswith("timing."):
                    summary = self.get_metric_summary(name)
                    if summary:
                        timing_summaries[name] = summary
            
            return {
                "uptime_seconds": uptime,
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "timing_summaries": timing_summaries,
                "total_metric_points": sum(len(points) for points in self.metrics.values())
            }
    
    def clear_old_metrics(self, older_than: timedelta = timedelta(hours=1)):
        """Clear metrics older than specified time."""
        with self.lock:
            cutoff_time = time.time() - older_than.total_seconds()
            
            for name, points in self.metrics.items():
                # Remove old points
                while points and points[0].timestamp < cutoff_time:
                    points.popleft()


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_http_request(method: str, status_code: int, duration: float, cached: bool = False):
    """Record HTTP request metrics."""
    collector = get_metrics_collector()
    
    # Record timing
    collector.record_timing("http_request", duration, {
        "method": method,
        "status_class": f"{status_code // 100}xx",
        "cached": str(cached)
    })
    
    # Increment counters
    collector.increment_counter("http_requests_total", 1, {
        "method": method,
        "status_code": str(status_code)
    })
    
    if cached:
        collector.increment_counter("http_requests_cached", 1)
    
    if 200 <= status_code < 300:
        collector.increment_counter("http_requests_success", 1)
    elif status_code >= 400:
        collector.increment_counter("http_requests_error", 1)


def record_storage_operation(operation: str, storage_type: str, duration: float, success: bool):
    """Record storage operation metrics."""
    collector = get_metrics_collector()
    
    collector.record_timing("storage_operation", duration, {
        "operation": operation,
        "storage_type": storage_type,
        "success": str(success)
    })
    
    collector.increment_counter("storage_operations_total", 1, {
        "operation": operation,
        "storage_type": storage_type
    })
    
    if success:
        collector.increment_counter("storage_operations_success", 1)
    else:
        collector.increment_counter("storage_operations_error", 1)


def record_template_operation(operation: str, duration: float, success: bool):
    """Record template operation metrics."""
    collector = get_metrics_collector()
    
    collector.record_timing("template_operation", duration, {
        "operation": operation,
        "success": str(success)
    })
    
    collector.increment_counter("template_operations_total", 1, {
        "operation": operation
    })


def record_ai_operation(operation: str, duration: float, success: bool, service: str = "gemini"):
    """Record AI operation metrics."""
    collector = get_metrics_collector()
    
    collector.record_timing("ai_operation", duration, {
        "operation": operation,
        "service": service,
        "success": str(success)
    })
    
    collector.increment_counter("ai_operations_total", 1, {
        "operation": operation,
        "service": service
    })


def set_system_metrics():
    """Set system-level gauge metrics."""
    collector = get_metrics_collector()
    
    try:
        import psutil
        
        # Memory usage
        memory = psutil.virtual_memory()
        collector.set_gauge("system_memory_used_bytes", memory.used)
        collector.set_gauge("system_memory_percent", memory.percent)
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        collector.set_gauge("system_cpu_percent", cpu_percent)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        collector.set_gauge("system_disk_used_bytes", disk.used)
        collector.set_gauge("system_disk_percent", (disk.used / disk.total) * 100)
        
    except ImportError:
        # psutil not available, skip system metrics
        pass
    except Exception:
        # Error getting system metrics, skip
        pass


class MetricsTimer:
    """Context manager for timing operations."""
    
    def __init__(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            success = exc_type is None
            
            # Add success tag
            tags = self.tags.copy()
            tags["success"] = str(success)
            
            get_metrics_collector().record_timing(self.metric_name, duration, tags)


def metrics_timer(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with MetricsTimer(metric_name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_performance_report() -> Dict[str, Any]:
    """Get a comprehensive performance report."""
    collector = get_metrics_collector()
    metrics = collector.get_all_metrics()
    
    # Calculate some derived metrics
    report = {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": metrics["uptime_seconds"],
        "summary": {}
    }
    
    # HTTP request summary
    if "counter.http_requests_total" in metrics["counters"]:
        total_requests = metrics["counters"]["counter.http_requests_total"]
        success_requests = metrics["counters"].get("counter.http_requests_success", 0)
        cached_requests = metrics["counters"].get("counter.http_requests_cached", 0)
        
        report["summary"]["http"] = {
            "total_requests": total_requests,
            "success_rate": (success_requests / total_requests) * 100 if total_requests > 0 else 0,
            "cache_hit_rate": (cached_requests / total_requests) * 100 if total_requests > 0 else 0
        }
        
        # Add timing summary if available
        if "timing.http_request" in metrics["timing_summaries"]:
            timing = metrics["timing_summaries"]["timing.http_request"]
            report["summary"]["http"]["avg_response_time_ms"] = timing.avg * 1000
            report["summary"]["http"]["p95_response_time_ms"] = timing.p95 * 1000
    
    # Storage operation summary
    storage_ops = metrics["counters"].get("counter.storage_operations_total", 0)
    if storage_ops > 0:
        storage_success = metrics["counters"].get("counter.storage_operations_success", 0)
        report["summary"]["storage"] = {
            "total_operations": storage_ops,
            "success_rate": (storage_success / storage_ops) * 100
        }
    
    # System metrics
    if "gauge.system_memory_percent" in metrics["gauges"]:
        report["summary"]["system"] = {
            "memory_usage_percent": metrics["gauges"]["gauge.system_memory_percent"],
            "cpu_usage_percent": metrics["gauges"].get("gauge.system_cpu_percent", 0),
            "disk_usage_percent": metrics["gauges"].get("gauge.system_disk_percent", 0)
        }
    
    return report