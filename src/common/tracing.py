"""
OpenTelemetry tracing configuration for the multi-agent pipeline.
Provides distributed tracing capabilities using Jaeger.
"""

import os
import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

class TracingConfig:
    """Configuration for OpenTelemetry tracing"""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
        self.enabled = os.getenv("TRACING_ENABLED", "true").lower() == "true"
        self.sample_rate = float(os.getenv("TRACING_SAMPLE_RATE", "1.0"))
        
    def setup_tracing(self) -> Optional[trace.Tracer]:
        """Initialize OpenTelemetry tracing with Jaeger exporter"""
        
        if not self.enabled:
            logger.info("Tracing disabled by configuration")
            return None
            
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": self.service_version,
                "service.namespace": "mcp-agent-swarm"
            })
            
            # Create tracer provider
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            
            # Create Jaeger exporter
            jaeger_exporter = JaegerExporter(
                endpoint=self.jaeger_endpoint,
            )
            
            # Create span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            provider.add_span_processor(span_processor)
            
            # Get tracer
            tracer = trace.get_tracer(self.service_name)
            
            logger.info(f"Tracing initialized for {self.service_name} -> {self.jaeger_endpoint}")
            return tracer
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            return None
    
    def instrument_fastapi(self, app):
        """Auto-instrument FastAPI application"""
        if self.enabled:
            try:
                FastAPIInstrumentor.instrument_app(app)
                logger.info("FastAPI instrumentation enabled")
            except Exception as e:
                logger.error(f"Failed to instrument FastAPI: {e}")
    
    def instrument_requests(self):
        """Auto-instrument requests library"""
        if self.enabled:
            try:
                RequestsInstrumentor().instrument()
                logger.info("Requests instrumentation enabled")
            except Exception as e:
                logger.error(f"Failed to instrument requests: {e}")
    
    def instrument_logging(self):
        """Auto-instrument logging"""
        if self.enabled:
            try:
                LoggingInstrumentor().instrument(set_logging_format=True)
                logger.info("Logging instrumentation enabled")
            except Exception as e:
                logger.error(f"Failed to instrument logging: {e}")

def setup_agent_tracing(service_name: str, app=None) -> Optional[trace.Tracer]:
    """
    Convenience function to set up tracing for an agent service
    
    Args:
        service_name: Name of the service (e.g., "api-gateway", "analysis-agent")
        app: FastAPI application instance (optional)
    
    Returns:
        Tracer instance or None if tracing is disabled
    """
    config = TracingConfig(service_name)
    
    # Set up basic tracing
    tracer = config.setup_tracing()
    
    # Instrument libraries
    config.instrument_requests()
    config.instrument_logging()
    
    # Instrument FastAPI if app provided
    if app:
        config.instrument_fastapi(app)
    
    return tracer

# Context manager for creating spans
class trace_operation:
    """Context manager for creating custom spans"""
    
    def __init__(self, tracer: Optional[trace.Tracer], operation_name: str, **attributes):
        self.tracer = tracer
        self.operation_name = operation_name
        self.attributes = attributes
        self.span = None
    
    def __enter__(self):
        if self.tracer is None:
            # No-op when tracer is None
            return None
            
        self.span = self.tracer.start_span(self.operation_name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, str(value))
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span is None:
            # No-op when span is None
            return
            
        if exc_type:
            self.span.record_exception(exc_val)
            self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
        else:
            self.span.set_status(trace.Status(trace.StatusCode.OK))
        self.span.end()

# Decorators for tracing functions
def trace_async_function(tracer: trace.Tracer, operation_name: str = None):
    """Decorator to trace async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with trace_operation(tracer, name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def trace_function(tracer: trace.Tracer, operation_name: str = None):
    """Decorator to trace regular functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with trace_operation(tracer, name):
                return func(*args, **kwargs)
        return wrapper
    return decorator 