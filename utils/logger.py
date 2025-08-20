"""
Logging utilities for tracking performance, costs, and errors.
"""

import logging
import time
import functools
from typing import Dict, Any, Optional
from datetime import datetime
import json

class DocumentExtractionLogger:
    """Custom logger for document extraction with performance and cost tracking."""
    
    def __init__(self, name: str = "doc_extraction", level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Metrics storage
        self.metrics = {
            "api_calls": 0,
            "total_tokens": 0,
            "total_cost_estimate": 0.0,
            "processing_times": [],
            "errors": []
        }
    
    def log_api_call(self, model: str, input_tokens: int, output_tokens: int, 
                     latency: float, operation: str = "extraction"):
        """Log API call metrics."""
        self.metrics["api_calls"] += 1
        self.metrics["total_tokens"] += input_tokens + output_tokens
        
        # Rough cost estimation (approximate rates)
        cost_per_1k_input = 0.00015  # $0.00015 per 1K input tokens for Gemini Flash
        cost_per_1k_output = 0.0006  # $0.0006 per 1K output tokens for Gemini Flash
        
        cost = (input_tokens / 1000 * cost_per_1k_input + 
                output_tokens / 1000 * cost_per_1k_output)
        self.metrics["total_cost_estimate"] += cost
        
        self.logger.info(
            f"API Call - Model: {model}, Operation: {operation}, "
            f"Input tokens: {input_tokens}, Output tokens: {output_tokens}, "
            f"Latency: {latency:.2f}s, Cost: ${cost:.4f}"
        )
    
    def log_processing_time(self, operation: str, duration: float, **kwargs):
        """Log processing time for operations."""
        self.metrics["processing_times"].append({
            "operation": operation,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
        
        self.logger.info(f"Processing time - {operation}: {duration:.2f}s")
    
    def log_error(self, operation: str, error: Exception, **kwargs):
        """Log errors with context."""
        error_info = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        self.metrics["errors"].append(error_info)
        self.logger.error(f"Error in {operation}: {error}", exc_info=True)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        avg_latency = 0
        if self.metrics["processing_times"]:
            avg_latency = sum(
                p["duration"] for p in self.metrics["processing_times"]
            ) / len(self.metrics["processing_times"])
        
        return {
            "total_api_calls": self.metrics["api_calls"],
            "total_tokens": self.metrics["total_tokens"],
            "estimated_cost": self.metrics["total_cost_estimate"],
            "average_latency": avg_latency,
            "total_errors": len(self.metrics["errors"]),
            "error_rate": len(self.metrics["errors"]) / max(1, self.metrics["api_calls"])
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            "api_calls": 0,
            "total_tokens": 0,
            "total_cost_estimate": 0.0,
            "processing_times": [],
            "errors": []
        }


def timer(logger: Optional[DocumentExtractionLogger] = None):
    """Decorator to time function execution."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if logger:
                    logger.log_processing_time(func.__name__, duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                if logger:
                    logger.log_error(func.__name__, e, duration=duration)
                
                raise
        return wrapper
    return decorator


# Global logger instance
_global_logger = None

def get_logger(name: str = "doc_extraction") -> DocumentExtractionLogger:
    """Get or create a global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = DocumentExtractionLogger(name)
    return _global_logger

