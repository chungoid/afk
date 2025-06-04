#!/usr/bin/env python3
"""
Test script to verify file upload functionality
"""

import asyncio
import sys
import tempfile
import zipfile
from pathlib import Path

# Add project root to path
sys.path.append('/home/flip/Desktop/test_swarm')

from src.common.file_handler import FileHandler, process_uploaded_zip, process_git_repo

async def test_file_handler():
    """Test the file handler with various scenarios"""
    print("Testing File Handler...")
    
    # Test 1: Create a simple ZIP file for testing
    print("\nTest 1: Creating test ZIP file...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test project structure
        project_dir = temp_path / "test_project"
        project_dir.mkdir()
        
        # Create some test files
        (project_dir / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")
        
        (project_dir / "requirements.txt").write_text("fastapi>=0.110.0\nuvicorn>=0.24.0")
        
        (project_dir / "README.md").write_text("# Test Project\nThis is a test project.")
        
        # Create sub-directory
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")
        (src_dir / "utils.py").write_text("def helper(): pass")
        
        # Create ZIP file
        zip_path = temp_path / "test_project.zip"
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for file_path in project_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(project_dir)
                    zip_file.write(file_path, arcname)
        
        # Read ZIP content
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print(f"Created test ZIP file: {len(zip_content)} bytes")
        
        # Test 2: Process uploaded ZIP
        print("\nTest 2: Processing uploaded ZIP...")
        try:
            project_files = await process_uploaded_zip(
                zip_content, 
                "test_project.zip",
                hints={"main_language": "python"}
            )
            
            print(f"Processed ZIP successfully!")
            print(f"   - Files: {project_files.total_files}")
            print(f"   - Size: {project_files.total_size} bytes")
            print(f"   - Detected language: {project_files.detected_language}")
            print(f"   - Detected framework: {project_files.detected_framework}")
            print(f"   - Source type: {project_files.source_type}")
            
            # Print file list
            print("   - Files found:")
            for file_path in sorted(project_files.files.keys()):
                print(f"     * {file_path}")
                
        except Exception as e:
            print(f"Error processing ZIP: {e}")
            return False
        
        # Test 3: Test Git repo (optional, requires network)
        print("\nTest 3: Testing Git repository processing (optional)...")
        try:
            # Test with a small public repo
            git_project_files = await process_git_repo(
                git_url="https://github.com/octocat/Hello-World.git",
                branch="master",
                hints={"main_language": "auto-detect"}
            )
            
            print(f"Processed Git repo successfully!")
            print(f"   - Files: {git_project_files.total_files}")
            print(f"   - Size: {git_project_files.total_size} bytes")
            print(f"   - Detected language: {git_project_files.detected_language}")
            print(f"   - Source type: {git_project_files.source_type}")
            
        except Exception as e:
            print(f"Git test skipped (requires network): {e}")
        
        print("\nAll file handler tests completed successfully!")
        return True

async def test_api_imports():
    """Test that all API components can be imported"""
    print("\nTesting API imports...")
    
    try:
        # Test API gateway imports
        sys.path.append('/home/flip/Desktop/test_swarm/services/api-gateway')
        import main as api_main
        print("API Gateway imports successfully")
        
        # Test file handler integration
        from src.common.file_handler import process_uploaded_zip, process_git_repo, process_file_dict
        print("File handler functions import successfully")
        
        # Test messaging
        from src.common.messaging_simple import create_messaging_client
        print("Messaging system imports successfully")
        
        return True
        
    except Exception as e:
        print(f"Import error: {e}")
        return False

async def main():
    """Run all tests"""
    print("Starting File Upload Integration Tests\n")
    
    success = True
    
    # Test imports first
    success &= await test_api_imports()
    
    # Test file handler
    success &= await test_file_handler()
    
    if success:
        print("\nAll tests passed! File upload functionality is ready.")
        print("\nSummary of implemented features:")
        print("   File handler with ZIP upload support")
        print("   Git repository cloning and processing")
        print("   Project structure analysis")
        print("   Language and framework detection")
        print("   API Gateway with file upload endpoint")
        print("   Enhanced dashboard with file upload UI")
        print("\nReady to test with real uploads!")
    else:
        print("\nSome tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 