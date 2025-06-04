"""
Analysis Steps - Core analysis functionality for the analysis agent.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AnalysisSteps:
    """
    Analysis steps that break down project requirements into structured tasks
    """
    
    def __init__(self):
        self.logger = logger
        
    async def analyze_project_requirements(
        self, 
        project_description: str, 
        requirements: List[str] = None, 
        constraints: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze project requirements and return structured analysis
        
        Args:
            project_description: Main project description
            requirements: List of specific requirements
            constraints: List of constraints/limitations
            
        Returns:
            Dictionary containing analysis results
        """
        
        requirements = requirements or []
        constraints = constraints or []
        
        self.logger.info(f"Analyzing project: {project_description[:100]}...")
        
        # Simulate analysis processing
        await asyncio.sleep(0.1)
        
        # Basic analysis structure
        analysis = {
            "summary": project_description,
            "complexity_score": self._assess_complexity(project_description, requirements),
            "estimated_duration_weeks": self._estimate_duration(requirements),
            "risk_factors": self._identify_risks(project_description, requirements, constraints),
            "technology_recommendations": self._recommend_technologies(project_description, requirements),
            "key_features": self._extract_features(project_description, requirements),
            "architecture_notes": self._suggest_architecture(project_description, requirements),
            "testing_requirements": self._identify_testing_needs(requirements),
            "deployment_considerations": self._analyze_deployment(requirements, constraints)
        }
        
        return analysis
        
    def _assess_complexity(self, description: str, requirements: List[str]) -> str:
        """Assess project complexity based on description and requirements"""
        complexity_indicators = [
            "microservice", "distributed", "real-time", "machine learning", 
            "ai", "blockchain", "oauth", "authentication", "payment", 
            "integration", "api", "database", "scalable", "performance"
        ]
        
        text = f"{description} {' '.join(requirements)}".lower()
        matches = sum(1 for indicator in complexity_indicators if indicator in text)
        
        if matches >= 8:
            return "high"
        elif matches >= 4:
            return "medium"
        else:
            return "low"
            
    def _estimate_duration(self, requirements: List[str]) -> int:
        """Estimate project duration in weeks"""
        base_weeks = 2
        additional_weeks = min(len(requirements) // 2, 20)  # Cap at 20 weeks
        return base_weeks + additional_weeks
        
    def _identify_risks(self, description: str, requirements: List[str], constraints: List[str]) -> List[str]:
        """Identify potential project risks"""
        risks = []
        text = f"{description} {' '.join(requirements)} {' '.join(constraints)}".lower()
        
        risk_patterns = {
            "integration": "Third-party integration complexity",
            "performance": "Performance and scalability challenges", 
            "security": "Security implementation complexity",
            "real-time": "Real-time processing requirements",
            "legacy": "Legacy system compatibility",
            "mobile": "Multi-platform mobile development",
            "payment": "Payment processing compliance",
            "gdpr": "Data privacy compliance requirements"
        }
        
        for pattern, risk in risk_patterns.items():
            if pattern in text:
                risks.append(risk)
                
        if len(requirements) > 15:
            risks.append("Large scope - risk of feature creep")
            
        return risks
        
    def _recommend_technologies(self, description: str, requirements: List[str]) -> List[str]:
        """Recommend suitable technologies"""
        text = f"{description} {' '.join(requirements)}".lower()
        technologies = []
        
        # Backend recommendations
        if "python" in text or "api" in text:
            technologies.append("FastAPI (Python backend)")
        elif "node" in text or "javascript" in text:
            technologies.append("Node.js with Express")
        else:
            technologies.append("FastAPI (Python backend)")
            
        # Frontend recommendations  
        if "web" in text or "frontend" in text:
            technologies.append("React with TypeScript")
            
        # Database recommendations
        if "database" in text:
            if "nosql" in text or "mongodb" in text:
                technologies.append("MongoDB (NoSQL)")
            else:
                technologies.append("PostgreSQL (SQL)")
                
        # Additional tech based on requirements
        if "auth" in text:
            technologies.append("JWT authentication")
        if "docker" in text or "container" in text:
            technologies.append("Docker containerization")
        if "test" in text:
            technologies.append("Pytest for testing")
            
        return technologies
        
    def _extract_features(self, description: str, requirements: List[str]) -> List[str]:
        """Extract key features from description and requirements"""
        features = []
        
        # Convert requirements to features
        for req in requirements:
            if req.strip():
                features.append(req.strip())
                
        # Extract features from description
        feature_keywords = {
            "auth": "User authentication",
            "login": "User login system", 
            "register": "User registration",
            "crud": "CRUD operations",
            "api": "REST API endpoints",
            "database": "Database integration",
            "search": "Search functionality",
            "upload": "File upload system",
            "notification": "Notification system",
            "dashboard": "Admin dashboard",
            "payment": "Payment processing",
            "report": "Reporting system"
        }
        
        desc_lower = description.lower()
        for keyword, feature in feature_keywords.items():
            if keyword in desc_lower and feature not in features:
                features.append(feature)
                
        return features[:10]  # Limit to top 10 features
        
    def _suggest_architecture(self, description: str, requirements: List[str]) -> List[str]:
        """Suggest architectural patterns"""
        text = f"{description} {' '.join(requirements)}".lower()
        architecture = []
        
        if "microservice" in text:
            architecture.append("Microservices architecture with service mesh")
        elif "api" in text:
            architecture.append("RESTful API with clean architecture")
        else:
            architecture.append("Monolithic architecture with modular design")
            
        if "database" in text:
            architecture.append("Repository pattern for data access")
            
        if "auth" in text:
            architecture.append("JWT-based authentication middleware")
            
        if "frontend" in text:
            architecture.append("Component-based frontend architecture")
            
        return architecture
        
    def _identify_testing_needs(self, requirements: List[str]) -> List[str]:
        """Identify testing requirements"""
        testing = ["Unit tests for core business logic"]
        
        req_text = " ".join(requirements).lower()
        
        if "api" in req_text:
            testing.append("API integration tests")
        if "frontend" in req_text or "ui" in req_text:
            testing.append("UI component tests")
        if "database" in req_text:
            testing.append("Database integration tests")
        if "auth" in req_text:
            testing.append("Authentication flow tests")
            
        testing.append("End-to-end user journey tests")
        return testing
        
    def _analyze_deployment(self, requirements: List[str], constraints: List[str]) -> List[str]:
        """Analyze deployment considerations"""
        deployment = []
        
        req_text = " ".join(requirements).lower() 
        constraint_text = " ".join(constraints).lower()
        
        if "docker" in req_text or "container" in req_text:
            deployment.append("Docker containerization")
            
        if "cloud" in req_text or "aws" in req_text or "azure" in req_text:
            deployment.append("Cloud deployment (AWS/Azure)")
        else:
            deployment.append("Container orchestration ready")
            
        if "database" in req_text:
            deployment.append("Database migration strategy")
            
        if "performance" in constraint_text or "scale" in constraint_text:
            deployment.append("Load balancing and auto-scaling")
            
        deployment.append("CI/CD pipeline setup")
        deployment.append("Environment configuration management")
        
        return deployment 