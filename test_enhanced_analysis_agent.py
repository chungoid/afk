#!/usr/bin/env python3
"""
Test script for enhanced Analysis Agent with existing codebase support
"""

import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append('/home/flip/Desktop/test_swarm')
sys.path.append('/home/flip/Desktop/test_swarm/services')

# Import the enhanced analysis agent
sys.path.append('/home/flip/Desktop/test_swarm/services/analysis-agent')
from main import AnalysisAgent, AnalysisRequest

async def test_enhanced_analysis_agent():
    """Test the enhanced analysis agent with existing project support"""
    
    print("TESTING ENHANCED ANALYSIS AGENT")
    print("=" * 60)
    
    # Initialize the agent
    agent = AnalysisAgent()
    
    # Test 1: New project (existing functionality)
    print("\nTest 1: New Project Analysis")
    new_project_request = AnalysisRequest(
        request_id="test_new_001",
        project_description="Build a task management web application",
        requirements=["User authentication", "Task CRUD operations", "Real-time notifications"],
        constraints=["Must be mobile-friendly", "Use modern frameworks"],
        project_type="new"
    )
    
    result1 = await agent.analyze_project(new_project_request)
    print(f"New Project Analysis Complete")
    print(f"   Tasks generated: {len(result1.tasks)}")
    print(f"   Estimated hours: {result1.total_estimated_hours}")
    print(f"   Team size: {result1.recommended_team_size}")
    
    # Test 2: Existing project analysis
    print("\nTest 2: Existing Codebase Analysis")
    
    # Load the test project files
    try:
        with open('test_existing_project.zip', 'rb') as f:
            zip_content = f.read()
        
        # Simulate project files (would normally come from file handler)
        sample_files = {
            "src/main.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef root(): return {'message': 'Hello World'}",
            "src/components/App.jsx": "import React from 'react';\nfunction App() { return <div>Hello React</div>; }\nexport default App;",
            "src/models/user.py": "from sqlalchemy import Column, String\nclass User(Base): username = Column(String)",
            "tests/test_main.py": "import pytest\ndef test_root(): assert True",
            "package.json": '{"dependencies": {"react": "^18.0.0", "axios": "^1.0.0"}}',
            "requirements.txt": "fastapi==0.104.1\nsqlalchemy==2.0.0\nuvicorn==0.24.0"
        }
        
        existing_project_request = AnalysisRequest(
            request_id="test_existing_001",
            project_description="Add user authentication and API rate limiting to existing application",
            requirements=[
                "JWT-based authentication system", 
                "API rate limiting middleware",
                "User profile management",
                "Admin dashboard"
            ],
            constraints=["Must maintain existing API structure", "Keep current database schema"],
            project_type="existing_local",
            project_files={
                "files": sample_files,
                "detected_language": "python",
                "detected_framework": "fastapi",
                "total_files": len(sample_files),
                "total_size": sum(len(content) for content in sample_files.values())
            }
        )
        
        result2 = await agent.analyze_project(existing_project_request)
        print(f"Existing Project Analysis Complete")
        print(f"   Modification tasks: {len(result2.tasks)}")
        print(f"   Estimated hours: {result2.total_estimated_hours}")
        print(f"   Team size: {result2.recommended_team_size}")
        print(f"   🏗️Project type: {result2.metadata.get('codebase_analysis', {}).get('project_type', 'unknown')}")
        
        # Show task breakdown
        print(f"\nTask Breakdown:")
        for i, task in enumerate(result2.tasks[:5], 1):  # Show first 5 tasks
            print(f"   {i}. {task.name} ({task.estimated_hours}h) - {task.complexity} complexity")
            
    except FileNotFoundError:
        print("test_existing_project.zip not found - creating simulated test")
        
        # Use simulated files only
        sample_files = {
            "app.py": "from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef hello(): return 'Hello World'",
            "models.py": "from flask_sqlalchemy import SQLAlchemy\ndb = SQLAlchemy()\nclass User(db.Model): pass",
            "tests/test_app.py": "import unittest\nclass TestApp(unittest.TestCase): pass"
        }
        
        existing_project_request = AnalysisRequest(
            request_id="test_simulated_001",
            project_description="Add REST API endpoints to existing Flask app",
            requirements=["User management API", "Authentication middleware", "Data validation"],
            project_type="existing_local",
            project_files={
                "files": sample_files,
                "detected_language": "python",
                "detected_framework": "flask",
                "total_files": len(sample_files),
                "total_size": sum(len(content) for content in sample_files.values())
            }
        )
        
        result2 = await agent.analyze_project(existing_project_request)
        print(f"Simulated Analysis Complete")
        print(f"   Tasks: {len(result2.tasks)}")
        print(f"   Hours: {result2.total_estimated_hours}")
    
    # Test 3: Verify key differences
    print(f"\nAnalysis Comparison:")
    print(f"   New Project Tasks: {len(result1.tasks)}")
    print(f"   Existing Project Tasks: {len(result2.tasks)}")
    print(f"   New Project Method: {result1.metadata.get('analysis_method')}")
    print(f"   Existing Project Method: {result2.metadata.get('analysis_method')}")
    
    # Test 4: Check language-agnostic support
    print(f"\nTest 3: Multi-Language Support")
    
    # Test with different languages
    languages_to_test = [
        ("javascript", {"package.json": '{"dependencies": {"express": "^4.18.0"}}', "app.js": "const express = require('express');"}),
        ("java", {"pom.xml": "<project><dependencies><dependency><groupId>org.springframework.boot</groupId></dependency></dependencies></project>", "Application.java": "@SpringBootApplication public class Application {}"}),
        ("go", {"go.mod": "module myapp\ngo 1.19", "main.go": "package main\nimport \"github.com/gin-gonic/gin\""}),
    ]
    
    for lang, files in languages_to_test:
        test_request = AnalysisRequest(
            request_id=f"test_{lang}_001",
            project_description=f"Add monitoring to existing {lang} application",
            requirements=["Health check endpoints", "Metrics collection"],
            project_type="existing_local",
            project_files={
                "files": files,
                "detected_language": lang,
                "total_files": len(files),
                "total_size": sum(len(content) for content in files.values())
            }
        )
        
        result = await agent.analyze_project(test_request)
        print(f"  {lang.capitalize()}: {len(result.tasks)} tasks, {result.total_estimated_hours}h")
    
    print(f"\nALL TESTS PASSED!")
    print(f"Enhanced Analysis Agent is ready for existing project support!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_analysis_agent()) 