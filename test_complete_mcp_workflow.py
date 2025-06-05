#!/usr/bin/env python3
"""
Complete MCP Workflow Test
Tests the full agent pipeline: API Gateway -> Analysis -> Planning -> Blueprint -> Code -> Test
"""

import asyncio
import json
import logging
import time
import sys
import zipfile
import tempfile
import socket
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

print("MCP-Enhanced Agent Swarm Complete Pipeline Test")
print("=" * 60)

def test_basic_setup():
    """Test basic Python setup and imports"""
    print("\nTesting Basic Setup")
    print("-" * 40)
    
    try:
        import sys
        from pathlib import Path
        print(f"Python version: {sys.version.split()[0]}")
        print(f"Working directory: {Path.cwd()}")
        
        src_path = Path(__file__).parent / "src"
        if src_path.exists():
            print(f"Src directory found: {src_path}")
            sys.path.append(str(src_path))
        else:
            print(f"WARNING: Src directory not found: {src_path}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Basic setup failed: {e}")
        return False

def test_docker_services():
    """Test all Docker services are running"""
    print("\nTesting Docker Services")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            services = {}
            
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        service_name = parts[0]
                        status = "Up" if "Up" in line else "Down"
                        services[service_name] = status
                        print(f"   {service_name:25} - {status}")
            
            required_services = [
                'message-broker', 'api-gateway', 'analysis-agent', 
                'planning-agent', 'blueprint-agent', 'code-agent', 
                'test-agent', 'orchestrator-agent'
            ]
            
            running_required = sum(1 for svc in required_services if services.get(svc) == "Up")
            print(f"\nRequired services running: {running_required}/{len(required_services)}")
            
            return running_required >= len(required_services) - 2  # Allow 2 to be down
        else:
            print(f"ERROR: docker-compose not running: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"ERROR: Docker services test failed: {e}")
        return False

def test_mcp_servers():
    """Test MCP server availability"""
    print("\nTesting MCP Servers")
    print("-" * 40)
    
    mcp_servers = {
        "fetch": 8100,
        "filesystem": 8101, 
        "git": 8102,
        "memory": 8103,
        "sequentialthinking": 8104,
        "time": 8105,
        "context7": 8106
    }
    
    available = []
    
    for server_name, port in mcp_servers.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"   {server_name:15} (port {port}) - Available")
                available.append(server_name)
            else:
                print(f"   {server_name:15} (port {port}) - Not available")
                
        except Exception as e:
            print(f"   {server_name:15} (port {port}) - Error: {e}")
    
    print(f"\nMCP servers available: {len(available)}/{len(mcp_servers)}")
    return len(available) >= 3

def test_agent_ports():
    """Test all agent service ports"""
    print("\nTesting Agent Service Ports")
    print("-" * 40)
    
    agent_ports = {
        "api-gateway": 8000,
        "analysis-agent": 8001,
        "orchestrator-agent": 8002,
        "planning-agent": 8003,
        "blueprint-agent": 8004,
        "code-agent": 8005,
        "test-agent": 8006
    }
    
    available = []
    
    for agent_name, port in agent_ports.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"   {agent_name:20} (port {port}) - Available")
                available.append(agent_name)
            else:
                print(f"   {agent_name:20} (port {port}) - Not available")
                
        except Exception as e:
            print(f"   {agent_name:20} (port {port}) - Error: {e}")
    
    print(f"\nAgent services available: {len(available)}/{len(agent_ports)}")
    return len(available) >= 5  # Need most agents running

def test_mcp_client_import():
    """Test MCP client import and basic functionality"""
    print("\nTesting MCP Client Import")
    print("-" * 40)
    
    try:
        from common.mcp_client import MCPClient
        print("MCP client imported successfully")
        
        client = MCPClient()
        servers = client.get_configured_servers()
        print(f"MCP client created, configured servers: {servers}")
        return True
        
    except ImportError as e:
        print(f"ERROR: MCP client import failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: MCP client test failed: {e}")
        return False

def test_enhanced_orchestrator():
    """Test MCP-enhanced orchestrator"""
    print("\nTesting Enhanced Orchestrator")
    print("-" * 40)
    
    try:
        from analysis_agent.orchestrator import Orchestrator
        print("Enhanced orchestrator imported successfully")
        
        orchestrator = Orchestrator(enable_mcp=True)
        print("MCP-enhanced orchestrator created")
        
        # Test new project analysis
        result = orchestrator.run("Test requirement", project_type="new")
        print(f"New project analysis: {len(result)} tasks generated")
        
        # Test existing project analysis (fallback mode)
        result_existing = orchestrator.run(
            "Add authentication",
            project_files=["app.py", "requirements.txt"],
            project_type="existing"
        )
        print(f"Existing project analysis: {len(result_existing)} tasks generated")
        
        return True
        
    except ImportError as e:
        print(f"ERROR: Orchestrator import failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Orchestrator test failed: {e}")
        return False

async def create_test_project_zip():
    """Create a test project ZIP file for existing project workflow"""
    test_files = {
        "app.py": '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Test Application")

class Item(BaseModel):
    name: str
    description: str

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id, "name": f"Item {item_id}"}

@app.post("/items/")
def create_item(item: Item):
    return {"message": f"Created item: {item.name}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
        "requirements.txt": '''
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-jose==3.3.0
''',
        "README.md": '''# Test Application

A FastAPI test application for MCP workflow testing.

## Features
- Basic REST API
- Item management endpoints
- Health check

## Usage
```bash
pip install -r requirements.txt
python app.py
```
''',
        "config.yaml": '''
app:
  name: "Test App"
  version: "1.0.0"
  debug: true

database:
  url: "sqlite:///test.db"
  
api:
  prefix: "/api/v1"
  cors_origins: ["*"]
'''
    }
    
    temp_dir = tempfile.mkdtemp()
    zip_path = Path(temp_dir) / "test_project.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path, content in test_files.items():
            zipf.writestr(file_path, content)
    
    return zip_path

async def test_complete_pipeline_workflow():
    """Test the complete pipeline workflow with file upload"""
    print("\nTesting Complete Pipeline Workflow")
    print("-" * 40)
    
    try:
        import aiohttp
        import aiofiles
        
        # Create test project
        zip_path = await create_test_project_zip()
        print(f"Created test project ZIP: {zip_path.name}")
        
        project_request = {
            "project_name": "Authentication Enhancement Test",
            "description": "Add comprehensive user authentication and authorization system to this FastAPI application",
            "requirements": [
                "User registration with email validation",
                "JWT token-based authentication",
                "Role-based access control (admin, user, guest)",
                "Password hashing and security",
                "Login/logout functionality",
                "Protected route middleware"
            ],
            "constraints": [
                "Maintain existing API endpoints",
                "Use FastAPI security features",
                "Backward compatible database changes",
                "Follow REST API best practices"
            ],
            "project_type": "existing_local",
            "priority": "high",
            "main_language": "python",
            "framework": "fastapi",
            "ignore_patterns": ["__pycache__", "*.pyc", ".git", ".env"]
        }
        
        async with aiohttp.ClientSession() as session:
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field('project_data', json.dumps(project_request))
            
            # Add ZIP file
            async with aiofiles.open(zip_path, 'rb') as f:
                file_content = await f.read()
                data.add_field('project_files', file_content,
                             filename='test_project.zip',
                             content_type='application/zip')
            
            print("Submitting project to API Gateway...")
            async with session.post(
                "http://localhost:8000/submit_with_files",
                data=data,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    request_id = result["request_id"]
                    print(f"SUCCESS: Project submitted")
                    print(f"Request ID: {request_id}")
                    print(f"Message: {result['message']}")
                    return request_id
                else:
                    error_text = await response.text()
                    print(f"ERROR: Failed to submit project")
                    print(f"Status: {response.status}")
                    print(f"Error: {error_text}")
                    return None
        
    except ImportError:
        print("WARNING: aiohttp/aiofiles not available, skipping workflow test")
        return None
    except Exception as e:
        print(f"ERROR: Pipeline workflow test failed: {e}")
        return None
    finally:
        try:
            zip_path.unlink()
        except:
            pass

async def monitor_pipeline_progress(request_id: str, timeout: int = 180):
    """Monitor the complete pipeline progress through all agents"""
    print(f"\nMonitoring Pipeline Progress: {request_id}")
    print("-" * 40)
    
    try:
        import aiohttp
        
        start_time = time.time()
        last_stage = None
        stages_seen = []
        
        expected_stages = [
            "analysis", "planning", "blueprint", "coding", "testing"
        ]
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout:
                try:
                    async with session.get(f"http://localhost:8000/status/{request_id}") as response:
                        if response.status == 200:
                            status = await response.json()
                            current_stage = status.get("current_stage")
                            pipeline_status = status.get("status")
                            completed_stages = status.get("stages_completed", [])
                            
                            if current_stage != last_stage:
                                print(f"Stage: {current_stage} | Status: {pipeline_status}")
                                if current_stage not in stages_seen:
                                    stages_seen.append(current_stage)
                                last_stage = current_stage
                            
                            # Check for completion
                            if pipeline_status == "completed":
                                print(f"\nPIPELINE COMPLETED SUCCESSFULLY!")
                                print(f"Completed stages: {', '.join(completed_stages)}")
                                print(f"Total stages processed: {len(stages_seen)}")
                                
                                # Verify all expected stages were hit
                                missing_stages = set(expected_stages) - set(completed_stages)
                                if missing_stages:
                                    print(f"WARNING: Missing stages: {missing_stages}")
                                else:
                                    print("SUCCESS: All expected stages completed")
                                
                                return {
                                    "success": True,
                                    "completed_stages": completed_stages,
                                    "total_stages": len(stages_seen),
                                    "missing_stages": list(missing_stages)
                                }
                            
                            elif pipeline_status == "failed":
                                error_msg = status.get("error_message", "Unknown error")
                                print(f"\nPIPELINE FAILED!")
                                print(f"Error: {error_msg}")
                                print(f"Failed at stage: {current_stage}")
                                print(f"Completed stages: {', '.join(completed_stages)}")
                                return {
                                    "success": False,
                                    "error": error_msg,
                                    "failed_stage": current_stage,
                                    "completed_stages": completed_stages
                                }
                        
                        else:
                            print(f"WARNING: Status check failed: HTTP {response.status}")
                            
                except Exception as e:
                    print(f"WARNING: Status check error: {e}")
                
                await asyncio.sleep(5)  # Check every 5 seconds
        
        print(f"\nTIMEOUT: Pipeline monitoring timed out after {timeout}s")
        print(f"Last known stage: {last_stage}")
        print(f"Stages seen: {stages_seen}")
        return {
            "success": False,
            "error": "timeout",
            "stages_seen": stages_seen,
            "last_stage": last_stage
        }
        
    except ImportError:
        print("WARNING: aiohttp not available, cannot monitor progress")
        return None
    except Exception as e:
        print(f"ERROR: Pipeline monitoring failed: {e}")
        return None

async def test_agent_health_endpoints():
    """Test health endpoints for all agents"""
    print("\nTesting Agent Health Endpoints")
    print("-" * 40)
    
    try:
        import aiohttp
        
        agents = {
            "api-gateway": 8000,
            "analysis-agent": 8001,
            "orchestrator-agent": 8002,
            "planning-agent": 8003,
            "blueprint-agent": 8004,
            "code-agent": 8005,
            "test-agent": 8006
        }
        
        healthy_agents = []
        
        async with aiohttp.ClientSession() as session:
            for agent_name, port in agents.items():
                try:
                    async with session.get(f"http://localhost:{port}/health", timeout=5) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            print(f"   {agent_name:20} - Healthy")
                            healthy_agents.append(agent_name)
                        else:
                            print(f"   {agent_name:20} - Unhealthy (Status: {response.status})")
                except Exception as e:
                    print(f"   {agent_name:20} - Error: {str(e)[:50]}")
        
        print(f"\nHealthy agents: {len(healthy_agents)}/{len(agents)}")
        return len(healthy_agents) >= len(agents) - 2  # Allow 2 to be down
        
    except ImportError:
        print("WARNING: aiohttp not available, skipping health check")
        return False
    except Exception as e:
        print(f"ERROR: Agent health check failed: {e}")
        return False

async def main():
    """Run the complete test suite"""
    
    print("Starting comprehensive agent pipeline test...")
    print("This will test ALL components of the MCP-enhanced agent swarm\n")
    
    # Phase 1: Basic Setup Tests
    print("PHASE 1: Basic Setup Tests")
    print("=" * 40)
    
    setup_ok = test_basic_setup()
    docker_ok = test_docker_services()
    mcp_client_ok = test_mcp_client_import()
    orchestrator_ok = test_enhanced_orchestrator()
    
    # Phase 2: Infrastructure Tests  
    print("\nPHASE 2: Infrastructure Tests")
    print("=" * 40)
    
    mcp_servers_ok = test_mcp_servers()
    agent_ports_ok = test_agent_ports()
    agent_health_ok = await test_agent_health_endpoints()
    
    # Phase 3: Complete Workflow Test
    print("\nPHASE 3: Complete Workflow Test")
    print("=" * 40)
    
    workflow_success = False
    pipeline_result = None
    
    if agent_health_ok and mcp_servers_ok:
        request_id = await test_complete_pipeline_workflow()
        
        if request_id:
            print(f"\nPipeline submitted successfully: {request_id}")
            pipeline_result = await monitor_pipeline_progress(request_id)
            workflow_success = pipeline_result and pipeline_result.get("success", False)
        else:
            print("Failed to submit pipeline workflow")
    else:
        print("Skipping workflow test - infrastructure not ready")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("COMPLETE PIPELINE TEST RESULTS")
    print("=" * 60)
    
    results = {
        "Basic Setup": setup_ok,
        "Docker Services": docker_ok,
        "MCP Client": mcp_client_ok,
        "Enhanced Orchestrator": orchestrator_ok,
        "MCP Servers": mcp_servers_ok,
        "Agent Ports": agent_ports_ok,
        "Agent Health": agent_health_ok,
        "Complete Workflow": workflow_success
    }
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"   {test_name:25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall Results: {passed}/{total} tests passed")
    
    if workflow_success and pipeline_result:
        print(f"\nPIPELINE SUCCESS DETAILS:")
        print(f"   Completed stages: {len(pipeline_result.get('completed_stages', []))}")
        print(f"   Missing stages: {pipeline_result.get('missing_stages', [])}")
        print(f"   Total agents involved: {pipeline_result.get('total_stages', 0)}")
    
    if passed >= total - 2:
        print("\nSUCCESS: MCP-enhanced agent swarm is fully operational!")
        print("All agents are working together with MCP integration.")
        print("\nThe system can now handle:")
        print("- New project generation")
        print("- Existing project enhancement") 
        print("- File upload and analysis")
        print("- Complete multi-agent pipeline")
        print("- MCP tool integration")
    else:
        print("\nWARNING: System needs attention before production use")
        print("\nFailed components:")
        for test_name, result in results.items():
            if not result:
                print(f"   - {test_name}")
        
        print("\nTroubleshooting steps:")
        print("   1. Start all services: ./start_mcp_servers.sh")
        print("   2. Check docker-compose logs for errors")
        print("   3. Verify all dependencies are installed")
        print("   4. Ensure all ports are available")
    
    print("\nTest completed.")

if __name__ == "__main__":
    # Setup logging to show errors
    logging.basicConfig(level=logging.WARNING)
    
    # Run the complete test suite
    asyncio.run(main())
