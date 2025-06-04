"""
Task Analyzer - Breaks down analysis results into specific tasks.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class TaskAnalyzer:
    """
    Task analyzer that breaks down project analysis into specific executable tasks
    """
    
    def __init__(self):
        self.logger = logger
        
    async def analyze_and_breakdown(
        self, 
        project_description: str, 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Break down analysis results into specific tasks
        
        Args:
            project_description: Original project description
            analysis_result: Analysis results from AnalysisSteps
            
        Returns:
            Dictionary containing task breakdown
        """
        
        self.logger.info(f"Breaking down project into tasks: {project_description[:100]}...")
        
        # Simulate task breakdown processing
        await asyncio.sleep(0.1)
        
        # Extract information from analysis
        features = analysis_result.get("key_features", [])
        technologies = analysis_result.get("technology_recommendations", [])
        testing_needs = analysis_result.get("testing_requirements", [])
        deployment = analysis_result.get("deployment_considerations", [])
        complexity = analysis_result.get("complexity_score", "medium")
        
        # Generate tasks
        tasks = []
        task_id = 1
        
        # Setup and infrastructure tasks
        tasks.extend(self._generate_setup_tasks(task_id, technologies, deployment))
        task_id += len(tasks)
        
        # Core feature tasks
        feature_tasks = self._generate_feature_tasks(task_id, features, complexity)
        tasks.extend(feature_tasks)
        task_id += len(feature_tasks)
        
        # Testing tasks
        testing_tasks = self._generate_testing_tasks(task_id, testing_needs)
        tasks.extend(testing_tasks)
        task_id += len(testing_tasks)
        
        # Deployment tasks
        deployment_tasks = self._generate_deployment_tasks(task_id, deployment)
        tasks.extend(deployment_tasks)
        
        return {
            "tasks": tasks,
            "total_tasks": len(tasks),
            "estimated_total_hours": sum(task.get("estimated_hours", 8) for task in tasks),
            "complexity_assessment": complexity,
            "breakdown_metadata": {
                "feature_count": len(features),
                "technology_count": len(technologies),
                "testing_tasks": len(testing_tasks),
                "deployment_tasks": len(deployment_tasks)
            }
        }
        
    def _generate_setup_tasks(self, start_id: int, technologies: List[str], deployment: List[str]) -> List[Dict[str, Any]]:
        """Generate project setup and infrastructure tasks"""
        tasks = []
        
        # Project initialization
        tasks.append({
            "id": f"task_{start_id}",
            "name": "Project Initialization",
            "description": "Set up project structure, version control, and basic configuration",
            "type": "setup",
            "priority": 1,
            "estimated_hours": 4.0,
            "dependencies": [],
            "skills_required": ["git", "project-management"],
            "complexity": "low"
        })
        
        # Technology stack setup
        if any("fastapi" in tech.lower() for tech in technologies):
            tasks.append({
                "id": f"task_{start_id + 1}",
                "name": "FastAPI Backend Setup",
                "description": "Initialize FastAPI project with basic structure and dependencies",
                "type": "backend-setup",
                "priority": 2,
                "estimated_hours": 6.0,
                "dependencies": [f"task_{start_id}"],
                "skills_required": ["python", "fastapi"],
                "complexity": "medium"
            })
            
        if any("react" in tech.lower() for tech in technologies):
            tasks.append({
                "id": f"task_{start_id + len(tasks)}",
                "name": "React Frontend Setup",
                "description": "Initialize React application with TypeScript and basic components",
                "type": "frontend-setup", 
                "priority": 2,
                "estimated_hours": 6.0,
                "dependencies": [f"task_{start_id}"],
                "skills_required": ["javascript", "react", "typescript"],
                "complexity": "medium"
            })
            
        if any("database" in tech.lower() for tech in technologies):
            tasks.append({
                "id": f"task_{start_id + len(tasks)}",
                "name": "Database Setup",
                "description": "Set up database schema, connections, and basic models",
                "type": "database-setup",
                "priority": 2,
                "estimated_hours": 8.0,
                "dependencies": [f"task_{start_id}"],
                "skills_required": ["database", "sql"],
                "complexity": "medium"
            })
            
        return tasks
        
    def _generate_feature_tasks(self, start_id: int, features: List[str], complexity: str) -> List[Dict[str, Any]]:
        """Generate tasks for implementing specific features"""
        tasks = []
        
        # Complexity multiplier for estimation
        complexity_multiplier = {"low": 0.8, "medium": 1.0, "high": 1.5}.get(complexity, 1.0)
        
        for i, feature in enumerate(features):
            base_hours = self._estimate_feature_hours(feature)
            estimated_hours = base_hours * complexity_multiplier
            
            task = {
                "id": f"task_{start_id + i}",
                "name": f"Implement {feature}",
                "description": f"Design and implement {feature.lower()} functionality",
                "type": "feature-implementation",
                "priority": self._determine_feature_priority(feature),
                "estimated_hours": estimated_hours,
                "dependencies": self._determine_feature_dependencies(feature, start_id, i),
                "skills_required": self._determine_feature_skills(feature),
                "complexity": complexity
            }
            tasks.append(task)
            
        return tasks
        
    def _generate_testing_tasks(self, start_id: int, testing_needs: List[str]) -> List[Dict[str, Any]]:
        """Generate testing tasks"""
        tasks = []
        
        for i, test_type in enumerate(testing_needs):
            task = {
                "id": f"task_{start_id + i}",
                "name": f"Implement {test_type}",
                "description": f"Create and implement {test_type.lower()}",
                "type": "testing",
                "priority": 4,
                "estimated_hours": self._estimate_testing_hours(test_type),
                "dependencies": self._determine_testing_dependencies(test_type, start_id),
                "skills_required": ["testing", "quality-assurance"],
                "complexity": "medium"
            }
            tasks.append(task)
            
        return tasks
        
    def _generate_deployment_tasks(self, start_id: int, deployment: List[str]) -> List[Dict[str, Any]]:
        """Generate deployment and DevOps tasks"""
        tasks = []
        
        for i, deploy_item in enumerate(deployment):
            task = {
                "id": f"task_{start_id + i}",
                "name": f"Setup {deploy_item}",
                "description": f"Configure and implement {deploy_item.lower()}",
                "type": "deployment",
                "priority": 5,
                "estimated_hours": self._estimate_deployment_hours(deploy_item),
                "dependencies": [f"task_{start_id - 10}"],  # Depend on feature tasks
                "skills_required": ["devops", "deployment"],
                "complexity": "medium"
            }
            tasks.append(task)
            
        return tasks
        
    def _estimate_feature_hours(self, feature: str) -> float:
        """Estimate hours for implementing a feature"""
        feature_lower = feature.lower()
        
        if any(keyword in feature_lower for keyword in ["auth", "login", "register"]):
            return 16.0
        elif any(keyword in feature_lower for keyword in ["crud", "api"]):
            return 12.0
        elif any(keyword in feature_lower for keyword in ["payment", "integration"]):
            return 24.0
        elif any(keyword in feature_lower for keyword in ["search", "upload"]):
            return 10.0
        elif any(keyword in feature_lower for keyword in ["dashboard", "report"]):
            return 14.0
        else:
            return 8.0
            
    def _determine_feature_priority(self, feature: str) -> int:
        """Determine priority for a feature (1=highest, 5=lowest)"""
        feature_lower = feature.lower()
        
        if any(keyword in feature_lower for keyword in ["auth", "login", "database"]):
            return 1  # Core infrastructure
        elif any(keyword in feature_lower for keyword in ["crud", "api"]):
            return 2  # Core functionality
        elif any(keyword in feature_lower for keyword in ["dashboard", "admin"]):
            return 3  # Management features
        elif any(keyword in feature_lower for keyword in ["search", "notification"]):
            return 4  # Enhancement features
        else:
            return 3  # Default priority
            
    def _determine_feature_dependencies(self, feature: str, start_id: int, index: int) -> List[str]:
        """Determine dependencies for a feature"""
        feature_lower = feature.lower()
        dependencies = []
        
        # Most features depend on basic setup (assuming first few tasks are setup)
        if index > 0:  # Don't make the first feature depend on setup
            dependencies.append(f"task_{start_id - 5}")  # Assume setup tasks are before features
            
        # Auth features are typically foundational
        if any(keyword in feature_lower for keyword in ["dashboard", "admin", "user"]) and index > 0:
            dependencies.append(f"task_{start_id}")  # Depend on first feature (likely auth)
            
        return dependencies
        
    def _determine_feature_skills(self, feature: str) -> List[str]:
        """Determine required skills for a feature"""
        feature_lower = feature.lower()
        skills = ["programming"]
        
        if any(keyword in feature_lower for keyword in ["auth", "security"]):
            skills.extend(["security", "authentication"])
        if any(keyword in feature_lower for keyword in ["database", "crud"]):
            skills.extend(["database", "sql"])
        if any(keyword in feature_lower for keyword in ["api", "rest"]):
            skills.extend(["api-development", "http"])
        if any(keyword in feature_lower for keyword in ["frontend", "ui", "dashboard"]):
            skills.extend(["frontend", "ui-design"])
        if any(keyword in feature_lower for keyword in ["payment"]):
            skills.extend(["payment-integration", "security"])
            
        return skills
        
    def _estimate_testing_hours(self, test_type: str) -> float:
        """Estimate hours for testing tasks"""
        test_lower = test_type.lower()
        
        if "unit" in test_lower:
            return 6.0
        elif "integration" in test_lower:
            return 8.0
        elif "end-to-end" in test_lower:
            return 12.0
        elif "performance" in test_lower:
            return 10.0
        else:
            return 6.0
            
    def _determine_testing_dependencies(self, test_type: str, start_id: int) -> List[str]:
        """Determine dependencies for testing tasks"""
        # Testing tasks typically depend on implementation being complete
        return [f"task_{start_id - 5}"]  # Assume implementation tasks are before testing
        
    def _estimate_deployment_hours(self, deploy_item: str) -> float:
        """Estimate hours for deployment tasks"""
        deploy_lower = deploy_item.lower()
        
        if "docker" in deploy_lower:
            return 6.0
        elif "ci/cd" in deploy_lower or "pipeline" in deploy_lower:
            return 10.0
        elif "cloud" in deploy_lower:
            return 12.0
        elif "database" in deploy_lower:
            return 8.0
        else:
            return 6.0 