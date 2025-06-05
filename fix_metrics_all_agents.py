#!/usr/bin/env python3
"""
Script to enable proper Prometheus metrics in all agent services
"""

import os
import re
from pathlib import Path

# Define the services to fix
SERVICES = [
    "blueprint-agent",
    "code-agent", 
    "test-agent",
    "orchestrator-agent",
    "api-gateway"
]

def add_prometheus_import(content):
    """Add prometheus_client import to file content"""
    # Find the import section (after the first import)
    if 'prometheus_client' in content:
        print(f"  ✓ already has prometheus_client import")
        return content
    
    # Add prometheus import after other imports
    import_patterns = [
        (r'(import uvicorn\n)', r'\1from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST\n'),
        (r'(from fastapi import.*?\n)', r'\1from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST\n'),
        (r'(import asyncio\n.*?import logging\n)', r'\1from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST\n')
    ]
    
    for pattern, replacement in import_patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, replacement, content, count=1)
            print(f"  ✓ Added prometheus_client import")
            break
    else:
        # Fallback: add after the first few imports
        lines = content.split('\n')
        import_end = 10  # Default position
        for i, line in enumerate(lines[:20]):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1
        
        lines.insert(import_end, 'from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST')
        content = '\n'.join(lines)
        print(f"  ✓ Added prometheus_client import (fallback)")
    
    return content

def fix_dummy_metrics(content, service_name):
    """Replace DummyMetric classes with real Prometheus metrics"""
    
    # Remove all DummyMetric class definitions
    content = re.sub(r'class DummyMetric:.*?def __exit__\(self, \*args\): pass\s*', '', content, flags=re.DOTALL)
    
    # Define service-specific metrics
    metrics_map = {
        'blueprint-agent': {
            'BLUEPRINT_REQUESTS_TOTAL': "Counter('blueprint_requests_total', 'Total blueprint requests', ['status'])",
            'BLUEPRINT_DURATION': "Histogram('blueprint_duration_seconds', 'Blueprint generation time')",
            'BLUEPRINT_ERRORS': "Counter('blueprint_errors_total', 'Blueprint generation errors', ['error_type'])",
            'ACTIVE_BLUEPRINTS': "Gauge('active_blueprints', 'Active blueprint generations')",
        },
        'code-agent': {
            'CODE_REQUESTS_TOTAL': "Counter('code_requests_total', 'Total code generation requests', ['status'])",
            'CODE_DURATION': "Histogram('code_duration_seconds', 'Code generation time')",
            'CODE_ERRORS': "Counter('code_errors_total', 'Code generation errors', ['error_type'])",
            'ACTIVE_GENERATIONS': "Gauge('active_code_generations', 'Active code generations')",
        },
        'test-agent': {
            'TEST_REQUESTS_TOTAL': "Counter('test_requests_total', 'Total test requests', ['status'])",
            'TEST_DURATION': "Histogram('test_duration_seconds', 'Test execution time')",
            'TEST_ERRORS': "Counter('test_errors_total', 'Test errors', ['error_type'])",
            'ACTIVE_TESTS': "Gauge('active_tests', 'Active test executions')",
        },
        'orchestrator-agent': {
            'ORCHESTRATOR_REQUESTS_TOTAL': "Counter('orchestrator_requests_total', 'Total orchestrator requests', ['status'])",
            'ORCHESTRATOR_DURATION': "Histogram('orchestrator_duration_seconds', 'Orchestration time')",
            'ORCHESTRATOR_ERRORS': "Counter('orchestrator_errors_total', 'Orchestration errors', ['error_type'])",
            'ACTIVE_ORCHESTRATIONS': "Gauge('active_orchestrations', 'Active orchestrations')",
        },
        'api-gateway': {
            'REQUESTS_TOTAL': "Counter('gateway_requests_total', 'Total gateway requests', ['endpoint', 'method', 'status'])",
            'REQUEST_DURATION': "Histogram('gateway_request_duration_seconds', 'Gateway request duration')",
            'ACTIVE_PIPELINES': "Gauge('active_pipelines', 'Active pipelines')",
            'PIPELINE_SUBMISSIONS': "Counter('pipeline_submissions_total', 'Pipeline submissions', ['status'])",
        }
    }
    
    service_metrics = metrics_map.get(service_name, {})
    
    # Replace DummyMetric() assignments
    for metric_name, metric_definition in service_metrics.items():
        pattern = f"{metric_name} = DummyMetric\\(\\)"
        if re.search(pattern, content):
            content = re.sub(pattern, f"{metric_name} = {metric_definition}", content)
            print(f"  ✓ Replaced {metric_name} with real metric")
    
    return content

def fix_metrics_endpoint(content):
    """Fix the /metrics endpoint to return proper Prometheus format"""
    
    # Pattern to match the disabled metrics endpoint
    pattern = r'@app\.get\("/metrics"\)\s*async def metrics\(\):.*?return \{".*?metrics disabled.*?\}'
    
    replacement = '''@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi import Response
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )'''
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        print(f"  ✓ Fixed /metrics endpoint")
    
    return content

def fix_service(service_name):
    """Fix metrics for a specific service"""
    service_path = Path(f"services/{service_name}/main.py")
    
    if not service_path.exists():
        print(f"❌ Service {service_name} not found at {service_path}")
        return
    
    print(f"\n🔧 Fixing {service_name}...")
    
    # Read current content
    with open(service_path, 'r') as f:
        content = f.read()
    
    # Apply fixes
    content = add_prometheus_import(content)
    content = fix_dummy_metrics(content, service_name)
    content = fix_metrics_endpoint(content)
    
    # Write back
    with open(service_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {service_name}")

def main():
    """Main function to fix all services"""
    print("🚀 Fixing Prometheus metrics for all agent services...")
    
    for service in SERVICES:
        fix_service(service)
    
    print(f"\n✅ All {len(SERVICES)} services fixed!")
    print("\nNext steps:")
    print("1. Rebuild Docker containers")
    print("2. Test metrics endpoints")
    print("3. Verify Prometheus scraping")

if __name__ == "__main__":
    main() 