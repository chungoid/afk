"""
Artifact Persistence Service

This service manages the persistence of generated code artifacts to Git and metadata to Weaviate.
It works with the existing infrastructure (Gitea + Weaviate) to provide:
- Version control for generated code
- Semantic search across artifacts
- Project organization and history
"""

import os
import json
import time
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

import aiohttp
import weaviate

logger = logging.getLogger(__name__)


@dataclass
class ArtifactMetadata:
    """Metadata for a persisted artifact"""
    project_id: str
    project_name: str
    artifact_id: str
    file_path: str
    language: str
    module: str
    commit_hash: str
    git_repo_url: str
    created_at: float
    agent_name: str
    dependencies: List[str]
    content_summary: str
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ArtifactPersistenceService:
    """
    Service for persisting artifacts to Git and storing metadata in Weaviate
    """
    
    def __init__(self, 
                 git_base_url: str = None,
                 weaviate_url: str = None,
                 weaviate_class: str = "ProjectArtifacts"):
        
        self.git_base_url = git_base_url or os.getenv("GIT_URL", "http://git-server:3000")
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL", "http://weaviate:8080")
        self.weaviate_class = weaviate_class
        
        # Initialize Weaviate client
        self.weaviate_client = None
        self._initialize_weaviate()
    
    def _initialize_weaviate(self):
        """Initialize Weaviate client and schema"""
        try:
            self.weaviate_client = weaviate.Client(self.weaviate_url)
            self._ensure_schema_exists()
        except Exception as e:
            logger.warning(f"Failed to initialize Weaviate: {e}")
    
    def _ensure_schema_exists(self):
        """Ensure the Weaviate schema exists for artifacts"""
        try:
            # Check if class exists
            existing_classes = self.weaviate_client.schema.get()['classes']
            class_names = [cls['class'] for cls in existing_classes]
            
            if self.weaviate_class not in class_names:
                # Create the class schema
                artifact_schema = {
                    "class": self.weaviate_class,
                    "description": "Generated code artifacts and metadata",
                    "properties": [
                        {
                            "name": "project_id",
                            "dataType": ["string"],
                            "description": "Unique project identifier"
                        },
                        {
                            "name": "project_name", 
                            "dataType": ["string"],
                            "description": "Human readable project name"
                        },
                        {
                            "name": "artifact_id",
                            "dataType": ["string"],
                            "description": "Unique artifact identifier"
                        },
                        {
                            "name": "file_path",
                            "dataType": ["string"],
                            "description": "Path to the file in the repository"
                        },
                        {
                            "name": "language",
                            "dataType": ["string"],
                            "description": "Programming language of the artifact"
                        },
                        {
                            "name": "module",
                            "dataType": ["string"],
                            "description": "Module or component name"
                        },
                        {
                            "name": "commit_hash",
                            "dataType": ["string"],
                            "description": "Git commit hash"
                        },
                        {
                            "name": "git_repo_url",
                            "dataType": ["string"],
                            "description": "Git repository URL"
                        },
                        {
                            "name": "agent_name",
                            "dataType": ["string"],
                            "description": "Name of the agent that created this artifact"
                        },
                        {
                            "name": "content_summary",
                            "dataType": ["text"],
                            "description": "Summary of the artifact content for semantic search"
                        },
                        {
                            "name": "dependencies",
                            "dataType": ["string[]"],
                            "description": "List of dependencies"
                        },
                        {
                            "name": "tags",
                            "dataType": ["string[]"],
                            "description": "Tags for categorization"
                        },
                        {
                            "name": "created_at",
                            "dataType": ["number"],
                            "description": "Creation timestamp"
                        }
                    ]
                }
                
                self.weaviate_client.schema.create_class(artifact_schema)
                logger.info(f"Created Weaviate class: {self.weaviate_class}")
                
        except Exception as e:
            logger.error(f"Error ensuring Weaviate schema: {e}")
    
    async def persist_project_artifacts(self,
                                      project_id: str,
                                      project_name: str,
                                      artifacts: List[Dict[str, Any]],
                                      temp_path: Path,
                                      agent_name: str = "unknown") -> Dict[str, Any]:
        """
        Persist a complete project's artifacts to Git and metadata to Weaviate
        
        Args:
            project_id: Unique project identifier
            project_name: Human readable project name
            artifacts: List of artifact dicts with file_path, content, language, etc.
            temp_path: Temporary directory containing the artifacts
            agent_name: Name of the agent creating these artifacts
            
        Returns:
            Dict with persistence results
        """
        
        result = {
            "success": False,
            "git_repo_url": None,
            "commit_hash": None,
            "artifacts_stored": 0,
            "metadata_stored": 0,
            "errors": []
        }
        
        try:
            # 1. Persist to Git
            git_result = await self._persist_to_git(project_id, project_name, temp_path)
            result.update(git_result)
            
            if git_result["success"]:
                # 2. Store metadata in Weaviate
                metadata_result = await self._store_metadata(
                    project_id=project_id,
                    project_name=project_name,
                    artifacts=artifacts,
                    commit_hash=git_result["commit_hash"],
                    git_repo_url=git_result["git_repo_url"],
                    agent_name=agent_name
                )
                result.update(metadata_result)
            
            result["success"] = git_result["success"] and result.get("metadata_stored", 0) > 0
            
        except Exception as e:
            result["errors"].append(f"Persistence error: {str(e)}")
            logger.error(f"Error persisting project artifacts: {e}")
        
        return result
    
    async def _persist_to_git(self, project_id: str, project_name: str, temp_path: Path) -> Dict[str, Any]:
        """Persist artifacts to Git repository"""
        
        result = {
            "success": False,
            "git_repo_url": None,
            "commit_hash": None,
            "errors": []
        }
        
        try:
            # Create repository name
            repo_name = f"{project_name.lower().replace(' ', '-')}-{project_id[:8]}"
            git_repo_url = f"{self.git_base_url}/{repo_name}"
            
            # Initialize git repo in temp directory  
            subprocess.run(["git", "init"], cwd=temp_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "artifacts@pipeline.local"], 
                         cwd=temp_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Artifact Persistence Service"], 
                         cwd=temp_path, check=True, capture_output=True)
            
            # Add README with project info
            readme_content = f"""# {project_name}

Project ID: {project_id}
Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}

This project was automatically generated by the Multi-Agent Development Pipeline.

## Project Structure

Generated artifacts are organized as follows:
- `src/` - Source code files
- `tests/` - Test files  
- `deployment/` - Deployment configurations
- `docs/` - Documentation files

## Pipeline Information

This project was created through the following pipeline stages:
1. Analysis - Requirements analysis and task decomposition
2. Planning - Project planning and task sequencing  
3. Blueprint - Architecture design and specifications
4. Coding - Code generation and implementation
5. Testing & Deployment - Testing, quality assurance, and deployment

For more information about the pipeline, visit the project documentation.
"""
            
            readme_path = temp_path / "README.md"
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            
            # Add all files
            subprocess.run(["git", "add", "."], cwd=temp_path, check=True, capture_output=True)
            
            # Create commit
            commit_msg = f"Initial commit for {project_name} (ID: {project_id})"
            subprocess.run(["git", "commit", "-m", commit_msg], 
                         cwd=temp_path, check=True, capture_output=True)
            
            # Get commit hash
            git_result = subprocess.run(["git", "rev-parse", "HEAD"], 
                                      cwd=temp_path, check=True, capture_output=True, text=True)
            commit_hash = git_result.stdout.strip()
            
            result.update({
                "success": True,
                "git_repo_url": git_repo_url,
                "commit_hash": commit_hash
            })
            
            logger.info(f"Artifacts persisted to Git: {git_repo_url} ({commit_hash})")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"Git persistence error: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    async def _store_metadata(self,
                            project_id: str,
                            project_name: str,
                            artifacts: List[Dict[str, Any]],
                            commit_hash: str,
                            git_repo_url: str,
                            agent_name: str) -> Dict[str, Any]:
        """Store artifact metadata in Weaviate"""
        
        result = {
            "metadata_stored": 0,
            "errors": []
        }
        
        if not self.weaviate_client:
            result["errors"].append("Weaviate client not available")
            return result
        
        try:
            for artifact in artifacts:
                # Create metadata object
                metadata = ArtifactMetadata(
                    project_id=project_id,
                    project_name=project_name,
                    artifact_id=f"{project_id}_{artifact['file_path'].replace('/', '_')}",
                    file_path=artifact['file_path'],
                    language=artifact.get('language', 'unknown'),
                    module=artifact.get('module', 'unknown'),
                    commit_hash=commit_hash,
                    git_repo_url=git_repo_url,
                    created_at=time.time(),
                    agent_name=agent_name,
                    dependencies=artifact.get('dependencies', []),
                    content_summary=self._create_content_summary(artifact),
                    tags=self._extract_tags(artifact)
                )
                
                # Store in Weaviate
                self.weaviate_client.data_object.create(
                    data_object=asdict(metadata),
                    class_name=self.weaviate_class
                )
                
                result["metadata_stored"] += 1
            
            logger.info(f"Stored {result['metadata_stored']} artifact metadata objects in Weaviate")
            
        except Exception as e:
            error_msg = f"Metadata storage error: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _create_content_summary(self, artifact: Dict[str, Any]) -> str:
        """Create a summary of the artifact content for semantic search"""
        content = artifact.get('content', '')
        file_path = artifact.get('file_path', '')
        language = artifact.get('language', '')
        module = artifact.get('module', '')
        
        # Extract key information for semantic search
        summary_parts = [
            f"File: {file_path}",
            f"Language: {language}",
            f"Module: {module}"
        ]
        
        # Add content snippet (first few lines)
        if content:
            lines = content.split('\n')[:10]  # First 10 lines
            content_snippet = '\n'.join(lines)
            summary_parts.append(f"Content: {content_snippet}")
        
        return ' '.join(summary_parts)
    
    def _extract_tags(self, artifact: Dict[str, Any]) -> List[str]:
        """Extract tags from artifact for categorization"""
        tags = []
        
        # Add language tag
        if language := artifact.get('language'):
            tags.append(f"lang:{language}")
        
        # Add module tag
        if module := artifact.get('module'):
            tags.append(f"module:{module}")
        
        # Add file type tag
        file_path = artifact.get('file_path', '')
        if file_path:
            if file_path.startswith('src/'):
                tags.append('source-code')
            elif file_path.startswith('tests/'):
                tags.append('tests')
            elif file_path.startswith('deployment/'):
                tags.append('deployment')
            elif file_path.endswith('.md'):
                tags.append('documentation')
        
        return tags
    
    async def search_artifacts(self, 
                             query: str,
                             project_id: str = None,
                             language: str = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search artifacts using semantic search
        
        Args:
            query: Search query
            project_id: Optional project ID filter
            language: Optional language filter
            limit: Maximum number of results
            
        Returns:
            List of matching artifacts with metadata
        """
        
        if not self.weaviate_client:
            logger.warning("Weaviate client not available for search")
            return []
        
        try:
            # Build Weaviate query
            where_filter = None
            if project_id or language:
                conditions = []
                if project_id:
                    conditions.append({
                        "path": ["project_id"],
                        "operator": "Equal",
                        "valueString": project_id
                    })
                if language:
                    conditions.append({
                        "path": ["language"],
                        "operator": "Equal", 
                        "valueString": language
                    })
                
                where_filter = {
                    "operator": "And",
                    "operands": conditions
                } if len(conditions) > 1 else conditions[0]
            
            # Execute search
            result = self.weaviate_client.query \
                .get(self.weaviate_class, [
                    "project_id", "project_name", "artifact_id", "file_path",
                    "language", "module", "commit_hash", "git_repo_url",
                    "agent_name", "content_summary", "dependencies", "tags", "created_at"
                ]) \
                .with_near_text({"concepts": [query]}) \
                .with_limit(limit)
            
            if where_filter:
                result = result.with_where(where_filter)
            
            response = result.do()
            
            artifacts = response.get('data', {}).get('Get', {}).get(self.weaviate_class, [])
            
            logger.info(f"Found {len(artifacts)} matching artifacts for query: {query}")
            return artifacts
            
        except Exception as e:
            logger.error(f"Error searching artifacts: {e}")
            return []
    
    async def get_project_artifacts(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all artifacts for a specific project"""
        return await self.search_artifacts("", project_id=project_id, limit=100)
    
    async def get_project_history(self, project_name: str) -> List[Dict[str, Any]]:
        """Get version history for a project"""
        if not self.weaviate_client:
            return []
        
        try:
            result = self.weaviate_client.query \
                .get(self.weaviate_class, [
                    "project_id", "project_name", "commit_hash", 
                    "git_repo_url", "created_at", "agent_name"
                ]) \
                .with_where({
                    "path": ["project_name"],
                    "operator": "Equal",
                    "valueString": project_name
                }) \
                .with_sort([{"path": ["created_at"], "order": "desc"}]) \
                .do()
            
            artifacts = result.get('data', {}).get('Get', {}).get(self.weaviate_class, [])
            
            # Group by commit_hash to get unique versions
            versions = {}
            for artifact in artifacts:
                commit_hash = artifact['commit_hash']
                if commit_hash not in versions:
                    versions[commit_hash] = {
                        "commit_hash": commit_hash,
                        "git_repo_url": artifact['git_repo_url'],
                        "created_at": artifact['created_at'],
                        "agent_name": artifact['agent_name'],
                        "artifact_count": 0
                    }
                versions[commit_hash]["artifact_count"] += 1
            
            return list(versions.values())
            
        except Exception as e:
            logger.error(f"Error getting project history: {e}")
            return []


# Global instance
artifact_service = ArtifactPersistenceService()


async def main():
    """Test the artifact persistence service"""
    # Example usage
    test_artifacts = [
        {
            "file_path": "src/main.py",
            "content": "# Main application file\nprint('Hello, World!')",
            "language": "python",
            "module": "main",
            "dependencies": ["fastapi"]
        },
        {
            "file_path": "tests/test_main.py", 
            "content": "# Test file\ndef test_main():\n    assert True",
            "language": "python",
            "module": "tests",
            "dependencies": ["pytest"]
        }
    ]
    
    # This would be called from the test-agent
    # result = await artifact_service.persist_project_artifacts(
    #     project_id="test_123",
    #     project_name="Test Project",
    #     artifacts=test_artifacts,
    #     temp_path=Path("/tmp/test"),
    #     agent_name="test-agent"
    # )
    # print(result)


if __name__ == "__main__":
    asyncio.run(main()) 