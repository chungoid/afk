#!/usr/bin/env python3
"""
Test script to submit a simple project request and generate Jaeger traces.
Run this after starting the services to see distributed tracing in action.
"""

import requests
import time
import json

def test_jaeger_tracing():
    """Submit a test project to generate traces"""
    
    # API Gateway URL
    api_url = "http://localhost:8000"
    
    print("🔍 Testing Jaeger Distributed Tracing")
    print("=" * 50)
    
    # Test project request
    test_project = {
        "project_name": "Jaeger Tracing Test",
        "description": "A simple test project to demonstrate distributed tracing across our multi-agent pipeline",
        "requirements": [
            "Create a simple Python web API",
            "Add basic error handling",
            "Include logging"
        ],
        "constraints": [
            "Keep it simple and minimal",
            "Use FastAPI framework"
        ],
        "priority": "medium",
        "technology_preferences": ["Python", "FastAPI"],
        "project_type": "new"
    }
    
    print(f"📤 Submitting test project: {test_project['project_name']}")
    
    try:
        # Submit the project
        response = requests.post(f"{api_url}/submit", json=test_project, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            request_id = result["request_id"]
            print(f"✅ Project submitted successfully!")
            print(f"   Request ID: {request_id}")
            print(f"   Status: {result['status']}")
            print(f"   Message: {result['message']}")
            
            # Wait a bit for the pipeline to process
            print("\n⏳ Waiting for pipeline to process...")
            time.sleep(5)
            
            # Check status
            status_response = requests.get(f"{api_url}/status/{request_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"📊 Current Status: {status.get('status', 'unknown')}")
                print(f"   Current Stage: {status.get('current_stage', 'unknown')}")
            
            print(f"\n🎯 View the traces in Jaeger:")
            print(f"   Dashboard: http://localhost:16686")
            print(f"   Service: mcp-agent-swarm.api-gateway")
            print(f"   Operation: submit_project_request")
            print(f"   Search for request_id: {request_id}")
            
            return request_id
            
        else:
            print(f"❌ Failed to submit project: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to API Gateway: {e}")
        print("   Make sure the services are running with: ./start.sh")
        return None

def check_jaeger_ui():
    """Check if Jaeger UI is accessible"""
    try:
        response = requests.get("http://localhost:16686", timeout=5)
        if response.status_code == 200:
            print("✅ Jaeger UI is accessible at http://localhost:16686")
            return True
        else:
            print(f"⚠️  Jaeger UI returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ Jaeger UI is not accessible at http://localhost:16686")
        print("   Make sure Jaeger is running in Docker Compose")
        return False

def main():
    print("🚀 Jaeger Tracing Test for MCP Agent Swarm")
    print("=" * 60)
    
    # Check if Jaeger UI is accessible
    if not check_jaeger_ui():
        return
    
    # Test the tracing
    request_id = test_jaeger_tracing()
    
    if request_id:
        print("\n" + "=" * 60)
        print("🎉 TRACING TEST COMPLETED!")
        print("=" * 60)
        print("\n📋 What to do next:")
        print(f"1. Open Jaeger UI: http://localhost:16686")
        print(f"2. Select service: 'mcp-agent-swarm.api-gateway'")
        print(f"3. Click 'Find Traces'")
        print(f"4. Look for traces with operation 'submit_project_request'")
        print(f"5. Click on a trace to see the detailed timeline")
        print(f"\n🔍 What you'll see in Jaeger:")
        print("• Request flow through your multi-agent pipeline")
        print("• Timing information for each operation")
        print("• Service dependencies and communication")
        print("• Error details if anything fails")
        print("• Custom attributes like request_id, project_name, etc.")
        
        print(f"\n📊 Advanced features to explore:")
        print("• Compare traces to identify performance patterns")
        print("• Use filters to find specific requests")
        print("• Analyze service dependencies in the dependency graph")
        print("• Monitor error rates and latency over time")

if __name__ == "__main__":
    main() 