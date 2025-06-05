#!/usr/bin/env python3
"""
Test script to demonstrate how existing project workflow works
"""

import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append('/home/flip/Desktop/test_swarm')

from src.common.file_handler import process_uploaded_zip, process_git_repo

async def demo_existing_project_workflow():
    """Demonstrate the complete existing project workflow"""
    
    print("EXISTING PROJECT WORKFLOW DEMONSTRATION")
    print("=" * 60)
    
    print("\nHow it works for existing projects:")
    print("""
When you select an existing project, you provide:

1. PROJECT IDENTIFICATION:
   - Project Name: "MyApp Enhancement" 
   - Project Type: "existing_git" or "existing_local"

2. PROJECT SOURCE:
   - For Git: Repository URL + branch
   - For Local: ZIP file upload

3. WHAT YOU WANT TO DO (the key part!):
   - Description: "Add user authentication and API rate limiting"
   - Requirements: List of specific features/changes you want
   - Technology Preferences: Any specific tech you want to use

The system then:
Analyzes your existing codebase 
Understands current architecture
Plans modifications that fit your existing patterns
Generates code that integrates seamlessly
""")

    # Test 1: Analyze the test project 
    print("\nSTEP 1: Analyzing the existing test project...")
    
    try:
        with open('test_existing_project.zip', 'rb') as f:
            zip_content = f.read()
        
        project_files = await process_uploaded_zip(
            zip_content, 
            "test_existing_project.zip",
            hints={"main_language": "auto-detect"}
        )
        
        print(f"Analysis complete!")
        print(f"   Files found: {project_files.total_files}")
        print(f"   Total size: {project_files.total_size} bytes")
        print(f"   Detected language: {project_files.detected_language}")
        print(f"   Detected framework: {project_files.detected_framework}")
        print(f"   Project structure:")
        
        structure = project_files.project_structure
        if structure:
            print(f"      • Type: {structure.get('directories', 'N/A')}")
            print(f"      • Has src directory: {structure.get('has_src_directory', False)}")
            print(f"      • Has tests: {structure.get('has_test_directory', False)}")
            print(f"      • Entry points: {structure.get('entry_points', [])}")
            print(f"      • Config files: {structure.get('config_files', [])}")
        
        print("\nFiles in project:")
        for file_path in sorted(project_files.files.keys())[:10]:  # Show first 10 files
            print(f"      • {file_path}")
        if project_files.total_files > 10:
            print(f"      ... and {project_files.total_files - 10} more files")
            
    except Exception as e:
        print(f"Error analyzing project: {e}")
        return False

    # Test 2: Show example request scenarios
    print("\n\nEXAMPLE SCENARIOS FOR EXISTING PROJECTS:")
    print("=" * 60)
    
    scenarios = [
        {
            "title": "Add Authentication",
            "description": "Add JWT-based user authentication to my existing FastAPI + React app",
            "requirements": [
                "User registration and login endpoints",
                "JWT token generation and validation", 
                "Protected routes in the API",
                "Login/signup forms in React frontend",
                "Session management"
            ],
            "what_happens": "System analyzes your FastAPI structure, adds auth endpoints to existing routes.py, creates auth middleware, updates React components to handle auth state"
        },
        {
            "title": "Add Analytics Dashboard", 
            "description": "Add a user analytics dashboard with charts and metrics",
            "requirements": [
                "Analytics data collection endpoints",
                "Charts and graphs using Chart.js or D3",
                "User activity tracking", 
                "Export functionality",
                "Real-time updates"
            ],
            "what_happens": "System creates new dashboard components in React, adds analytics endpoints to FastAPI, integrates with existing database models"
        },
        {
            "title": "Performance Optimization",
            "description": "Optimize my existing app for better performance and scalability",
            "requirements": [
                "Database query optimization",
                "Caching implementation (Redis)",
                "API response compression",
                "Frontend bundle optimization",
                "Database indexing"
            ],
            "what_happens": "System analyzes existing queries, adds caching layers, optimizes database schemas, updates build configuration"
        },
        {
            "title": "Technology Migration",
            "description": "Migrate from JavaScript to TypeScript in my React frontend",
            "requirements": [
                "Convert all .js files to .tsx/.ts",
                "Add proper type definitions",
                "Update build configuration",
                "Maintain existing functionality",
                "Add type-safe API calls"
            ],
            "what_happens": "System analyzes existing JS code, generates TypeScript equivalents with proper types, updates configs, maintains all existing features"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{scenario['title']}")
        print("-" * 40)
        print(f"What you'd describe: {scenario['description']}")
        print(f"Requirements you'd list:")
        for req in scenario['requirements']:
            print(f"   • {req}")
        print(f"What the system does: {scenario['what_happens']}")
        
    # Test 3: Show the actual API request format
    print("\n\nTECHNICAL: What gets sent to the API")
    print("=" * 60)
    
    example_request = {
        "project_name": "MyApp Enhancement",
        "description": "Add user authentication and API rate limiting to my existing FastAPI + React application",
        "requirements": [
            "JWT-based user authentication",
            "User registration and login endpoints", 
            "Protected API routes with middleware",
            "React login/signup components",
            "API rate limiting with Redis",
            "Session management"
        ],
        "project_type": "existing_local",  # or "existing_git"
        "priority": "high",
        "technology_preferences": ["FastAPI", "React", "TypeScript", "Redis", "JWT"],
        "main_language": "python",  # detected automatically
        "framework": "fastapi"     # detected automatically
    }
    
    print("Request payload:")
    print(json.dumps(example_request, indent=2))
    
    print("\nResponse includes:")
    print("   • Request ID for tracking")
    print("   • Analysis of existing codebase") 
    print("   • Integration plan")
    print("   • Generated code that fits existing patterns")
    print("   • Updated files that enhance current functionality")
    
    # Test 4: Show the difference vs new projects
    print("\n\nDIFFERENCE: Existing vs New Projects")
    print("=" * 60)
    
    comparison = """
NEW PROJECT:
├── You describe what you want to build
├── System creates everything from scratch  
├── Chooses optimal architecture/patterns
└── Generates complete new codebase

EXISTING PROJECT:
├── You describe what you want to ADD/CHANGE
├── System analyzes your current code
├── Understands your existing patterns/architecture  
├── Plans modifications that fit seamlessly
└── Generates code that enhances existing functionality

KEY DIFFERENCE: With existing projects, you describe CHANGES/ADDITIONS,
not the entire project. The system respects and builds upon what you have.
"""
    
    print(comparison)
    
    print("\n\nREADY TO TEST!")
    print("=" * 60)
    print("To test existing project workflow:")
    print("1. Start the API gateway: cd services/api-gateway && python main.py") 
    print("2. Go to: http://localhost:8000/dashboard")
    print("3. Select 'Local Project (Upload Files)' or 'Existing Git Repository'")
    print("4. Upload the test_existing_project.zip or enter a Git URL")
    print("5. In Description: 'Add user authentication system'")
    print("6. In Requirements: 'JWT auth, login/signup pages, protected routes'")
    print("7. Submit and watch the magic!")
    
    return True

async def main():
    """Run the demonstration"""
    print("Starting Existing Project Workflow Demo\n")
    
    success = await demo_existing_project_workflow()
    
    if success:
        print("\nDemo completed! You now understand how existing projects work.")
        print("\nKEY TAKEAWAY:")
        print("   For existing projects, you describe what you want to ADD or CHANGE,")
        print("   not rebuild the entire project. The system enhances what you have!")
    else:
        print("\nDemo failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main()) 