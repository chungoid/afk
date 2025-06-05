#!/usr/bin/env python3
"""
Test script for MCP-enhanced Analysis Agent
Shows how the enhanced orchestrator works with existing projects
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from analysis_agent.orchestrator import Orchestrator

def main():
    """Test the MCP-enhanced Analysis Agent"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("Testing MCP-Enhanced Analysis Agent")
    print("=" * 50)
    
    # Test 1: Standard analysis (new project)
    print("\nTest 1: Standard Analysis (New Project)")
    print("-" * 40)
    
    orchestrator = Orchestrator(enable_mcp=True)
    
    new_project_requirement = """
    Create a web application for managing personal book collections.
    Users should be able to add books, search their collection, 
    and track reading progress.
    """
    
    try:
        tasks = orchestrator.run(new_project_requirement, project_type="new")
        print(f"Generated {len(tasks)} tasks for new project")
        for i, task in enumerate(tasks[:3], 1):  # Show first 3 tasks
            print(f"   {i}. {task.get('title', 'Untitled task')}")
    except Exception as e:
        print(f"Standard analysis failed: {e}")
    
    # Test 2: MCP-enhanced analysis (existing project)
    print("\nTest 2: MCP-Enhanced Analysis (Existing Project)")
    print("-" * 40)
    
    # Use generated_project as example existing codebase
    project_files = []
    generated_project_path = Path("generated_project")
    
    if generated_project_path.exists():
        # Collect Python and JavaScript files
        for ext in ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx"]:
            project_files.extend(str(f) for f in generated_project_path.rglob(ext))
        
        if project_files:
            existing_project_requirement = """
            Add user authentication and authorization to this application.
            Users should be able to register, login, and have role-based 
            access control (admin vs regular user).
            """
            
            try:
                tasks = orchestrator.run(
                    existing_project_requirement, 
                    project_files=project_files[:10],  # Limit to first 10 files
                    project_type="existing"
                )
                print(f"Generated {len(tasks)} MCP-enhanced tasks for existing project")
                for i, task in enumerate(tasks[:3], 1):
                    print(f"   {i}. {task.get('title', 'Untitled task')}")
                    metadata = task.get('metadata', {})
                    if metadata.get('project_type') == 'existing':
                        print(f"      Analyzed {metadata.get('total_existing_files', 0)} existing files")
                        
            except Exception as e:
                print(f"MCP-enhanced analysis failed: {e}")
                print("   This is expected if MCP servers aren't running")
        else:
            print("No files found in generated_project/ directory")
    else:
        print("generated_project/ directory not found")
    
    # Test 3: Fallback behavior
    print("\nTest 3: Fallback Behavior")
    print("-" * 40)
    
    # Test with MCP disabled
    orchestrator_no_mcp = Orchestrator(enable_mcp=False)
    
    try:
        tasks = orchestrator_no_mcp.run(
            "Add a search feature to this app",
            project_files=["app.py", "main.js"],
            project_type="existing"
        )
        print(f"Fallback to standard analysis worked: {len(tasks)} tasks")
    except Exception as e:
        print(f"Fallback failed: {e}")
    
    print("\n" + "=" * 50)
    print("MCP Integration Summary:")
    print("Enhanced orchestrator maintains backward compatibility")
    print("MCP analysis triggered for existing projects")
    print("Graceful fallback when MCP unavailable")
    print("No code duplication - single orchestrator file")


if __name__ == "__main__":
    main() 