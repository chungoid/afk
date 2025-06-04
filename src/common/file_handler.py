"""
File Handler for Multi-Agent Pipeline

Supports multiple input sources:
- Local file uploads (ZIP, drag & drop)  
- Git repositories (GitHub, GitLab, local Git servers)
- Direct file content
"""

import os
import json
import tempfile
import zipfile
import asyncio
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class ProjectFiles:
    """Container for project files with metadata"""
    files: Dict[str, str]  # path -> content
    metadata: Dict[str, Any]
    source_type: str  # "upload", "git", "local"
    total_files: int
    total_size: int
    detected_language: Optional[str] = None
    detected_framework: Optional[str] = None
    project_structure: Optional[Dict[str, Any]] = None

@dataclass
class GitRepositoryInfo:
    """Git repository information"""
    url: str
    branch: str = "main"
    commit_hash: Optional[str] = None
    clone_depth: int = 1
    credentials: Optional[Dict[str, str]] = None

class FileHandler:
    """Handles various file input sources for the pipeline"""
    
    def __init__(self, max_file_size: int = 50 * 1024 * 1024):  # 50MB default
        self.max_file_size = max_file_size
        self.default_ignore_patterns = {
            ".git", ".github", ".gitignore", 
            "node_modules", "__pycache__", ".venv", ".env",
            "*.pyc", "*.pyo", "*.pyd", ".Python",
            "build", "dist", "*.egg-info", ".pytest_cache",
            ".DS_Store", "Thumbs.db", "*.log", "*.tmp",
            ".vscode", ".idea", "*.swp", "*.swo"
        }
        
    async def process_upload(self, 
                           uploaded_file: bytes, 
                           filename: str,
                           hints: Optional[Dict[str, Any]] = None) -> ProjectFiles:
        """Process uploaded ZIP file"""
        
        if not filename.lower().endswith('.zip'):
            raise ValueError("Only ZIP files are supported for upload")
            
        if len(uploaded_file) > self.max_file_size:
            raise ValueError(f"File too large (max {self.max_file_size // 1024 // 1024}MB)")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / filename
            
            # Save uploaded file
            with open(zip_path, 'wb') as f:
                f.write(uploaded_file)
            
            # Extract ZIP
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path / "extracted")
            except zipfile.BadZipFile:
                raise ValueError("Invalid ZIP file")
            
            extracted_path = temp_path / "extracted"
            
            # Process extracted files
            files = await self._process_directory(extracted_path, hints)
            
            return ProjectFiles(
                files=files,
                metadata={
                    "source": "upload",
                    "filename": filename,
                    "upload_size": len(uploaded_file),
                    "hints": hints or {}
                },
                source_type="upload",
                total_files=len(files),
                total_size=sum(len(content) for content in files.values())
            )
    
    async def process_git_repository(self, 
                                   git_info: GitRepositoryInfo,
                                   hints: Optional[Dict[str, Any]] = None) -> ProjectFiles:
        """Process Git repository"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_path = temp_path / "repo"
            
            # Clone repository
            await self._clone_repository(git_info, repo_path)
            
            # Get commit info
            commit_hash = await self._get_commit_hash(repo_path)
            
            # Process repository files
            files = await self._process_directory(repo_path, hints)
            
            return ProjectFiles(
                files=files,
                metadata={
                    "source": "git",
                    "git_url": git_info.url,
                    "git_branch": git_info.branch,
                    "commit_hash": commit_hash,
                    "hints": hints or {}
                },
                source_type="git",
                total_files=len(files),
                total_size=sum(len(content) for content in files.values())
            )
    
    async def process_local_files(self, 
                                files_dict: Dict[str, str],
                                hints: Optional[Dict[str, Any]] = None) -> ProjectFiles:
        """Process already provided file contents"""
        
        # Filter files based on ignore patterns
        filtered_files = {}
        ignore_patterns = self._get_ignore_patterns(hints)
        
        for file_path, content in files_dict.items():
            if not self._should_ignore_file(file_path, ignore_patterns):
                filtered_files[file_path] = content
        
        return ProjectFiles(
            files=filtered_files,
            metadata={
                "source": "local",
                "hints": hints or {}
            },
            source_type="local", 
            total_files=len(filtered_files),
            total_size=sum(len(content) for content in filtered_files.values())
        )
    
    async def _clone_repository(self, git_info: GitRepositoryInfo, target_path: Path):
        """Clone Git repository"""
        
        clone_cmd = [
            "git", "clone",
            "--depth", str(git_info.clone_depth),
            "--branch", git_info.branch,
            git_info.url,
            str(target_path)
        ]
        
        # Handle credentials if provided
        env = os.environ.copy()
        if git_info.credentials:
            if "username" in git_info.credentials and "password" in git_info.credentials:
                # For HTTPS repositories
                parsed_url = urlparse(git_info.url)
                authenticated_url = f"{parsed_url.scheme}://{git_info.credentials['username']}:{git_info.credentials['password']}@{parsed_url.netloc}{parsed_url.path}"
                clone_cmd[-2] = authenticated_url
        
        try:
            process = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Git clone failed"
                raise RuntimeError(f"Failed to clone repository: {error_msg}")
                
            logger.info(f"Successfully cloned {git_info.url} to {target_path}")
            
        except Exception as e:
            raise RuntimeError(f"Git clone error: {str(e)}")
    
    async def _get_commit_hash(self, repo_path: Path) -> str:
        """Get current commit hash from repository"""
        
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                logger.warning("Could not get commit hash")
                return "unknown"
                
        except Exception as e:
            logger.warning(f"Error getting commit hash: {e}")
            return "unknown"
    
    async def _process_directory(self, 
                               directory: Path, 
                               hints: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Process directory and extract file contents"""
        
        files = {}
        ignore_patterns = self._get_ignore_patterns(hints)
        
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
                
            relative_path = file_path.relative_to(directory)
            relative_path_str = str(relative_path).replace("\\", "/")  # Normalize path separators
            
            # Check if file should be ignored
            if self._should_ignore_file(relative_path_str, ignore_patterns):
                continue
            
            # Check file size
            if file_path.stat().st_size > 5 * 1024 * 1024:  # 5MB per file
                logger.warning(f"Skipping large file: {relative_path_str}")
                continue
            
            # Read file content
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    files[relative_path_str] = content
            except (UnicodeDecodeError, PermissionError):
                # Skip binary files or files we can't read
                logger.debug(f"Skipping unreadable file: {relative_path_str}")
                continue
            except Exception as e:
                logger.warning(f"Error reading file {relative_path_str}: {e}")
                continue
        
        return files
    
    def _get_ignore_patterns(self, hints: Optional[Dict[str, Any]] = None) -> set:
        """Get ignore patterns from hints or use defaults"""
        
        patterns = self.default_ignore_patterns.copy()
        
        if hints and "ignore_patterns" in hints:
            patterns.update(hints["ignore_patterns"])
        
        return patterns
    
    def _should_ignore_file(self, file_path: str, ignore_patterns: set) -> bool:
        """Check if file should be ignored"""
        
        file_path_lower = file_path.lower()
        
        for pattern in ignore_patterns:
            # Simple pattern matching
            if pattern.startswith("*"):
                if file_path_lower.endswith(pattern[1:]):
                    return True
            elif pattern.endswith("*"):
                if file_path_lower.startswith(pattern[:-1]):
                    return True
            elif pattern in file_path_lower:
                return True
                
        return False
    
    async def analyze_project_structure(self, project_files: ProjectFiles) -> ProjectFiles:
        """Analyze project structure and detect language/framework"""
        
        files = project_files.files
        
        # Detect primary language
        language_counts = {}
        for file_path in files.keys():
            ext = Path(file_path).suffix.lower()
            if ext in ['.py']:
                language_counts['python'] = language_counts.get('python', 0) + 1
            elif ext in ['.js', '.jsx']:
                language_counts['javascript'] = language_counts.get('javascript', 0) + 1
            elif ext in ['.ts', '.tsx']:
                language_counts['typescript'] = language_counts.get('typescript', 0) + 1
            elif ext in ['.java']:
                language_counts['java'] = language_counts.get('java', 0) + 1
            elif ext in ['.go']:
                language_counts['go'] = language_counts.get('go', 0) + 1
            elif ext in ['.rs']:
                language_counts['rust'] = language_counts.get('rust', 0) + 1
            elif ext in ['.php']:
                language_counts['php'] = language_counts.get('php', 0) + 1
            elif ext in ['.cs']:
                language_counts['csharp'] = language_counts.get('csharp', 0) + 1
        
        detected_language = max(language_counts, key=language_counts.get) if language_counts else None
        
        # Detect framework
        detected_framework = await self._detect_framework(files, detected_language)
        
        # Analyze project structure
        structure = self._analyze_structure(files)
        
        # Update project files with analysis
        project_files.detected_language = detected_language
        project_files.detected_framework = detected_framework
        project_files.project_structure = structure
        
        return project_files
    
    async def _detect_framework(self, files: Dict[str, str], language: Optional[str]) -> Optional[str]:
        """Detect framework based on files and language"""
        
        file_paths = set(files.keys())
        
        # Python frameworks
        if language == 'python':
            if 'requirements.txt' in files or 'pyproject.toml' in files:
                content = files.get('requirements.txt', '') + files.get('pyproject.toml', '')
                if 'fastapi' in content.lower():
                    return 'fastapi'
                elif 'django' in content.lower():
                    return 'django'
                elif 'flask' in content.lower():
                    return 'flask'
        
        # JavaScript/TypeScript frameworks
        elif language in ['javascript', 'typescript']:
            if 'package.json' in files:
                try:
                    package_json = json.loads(files['package.json'])
                    dependencies = {**package_json.get('dependencies', {}), **package_json.get('devDependencies', {})}
                    
                    if 'react' in dependencies:
                        return 'react'
                    elif 'vue' in dependencies:
                        return 'vue'
                    elif 'angular' in dependencies or '@angular/core' in dependencies:
                        return 'angular'
                    elif 'express' in dependencies:
                        return 'express'
                    elif 'next' in dependencies:
                        return 'nextjs'
                except json.JSONDecodeError:
                    pass
        
        # Java frameworks
        elif language == 'java':
            if 'pom.xml' in files:
                pom_content = files['pom.xml'].lower()
                if 'spring-boot' in pom_content:
                    return 'spring-boot'
                elif 'spring' in pom_content:
                    return 'spring'
        
        return None
    
    def _analyze_structure(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Analyze project structure"""
        
        # Get all directories
        directories = set()
        for file_path in files.keys():
            parts = Path(file_path).parts[:-1]  # Exclude filename
            for i in range(len(parts)):
                directories.add('/'.join(parts[:i+1]))
        
        # Common patterns
        has_src = any('src' in d for d in directories)
        has_tests = any('test' in d.lower() for d in directories)
        has_docs = any('doc' in d.lower() for d in directories)
        
        # Entry points
        entry_points = []
        common_entry_files = ['main.py', 'app.py', 'index.js', 'index.ts', 'main.js', 'server.js']
        for entry_file in common_entry_files:
            if entry_file in files or f"src/{entry_file}" in files:
                entry_points.append(entry_file)
        
        # Config files
        config_files = []
        common_config_files = [
            'requirements.txt', 'package.json', 'pom.xml', 'Cargo.toml',
            'Dockerfile', 'docker-compose.yml', '.env', 'config.py'
        ]
        for config_file in common_config_files:
            if config_file in files:
                config_files.append(config_file)
        
        return {
            "directories": sorted(directories),
            "has_src_directory": has_src,
            "has_test_directory": has_tests,
            "has_docs_directory": has_docs,
            "entry_points": entry_points,
            "config_files": config_files,
            "total_directories": len(directories),
            "file_extensions": list(set(Path(f).suffix for f in files.keys() if Path(f).suffix))
        }

# Convenience functions
async def process_uploaded_zip(uploaded_file: bytes, 
                             filename: str, 
                             hints: Optional[Dict[str, Any]] = None) -> ProjectFiles:
    """Process uploaded ZIP file"""
    handler = FileHandler()
    project_files = await handler.process_upload(uploaded_file, filename, hints)
    return await handler.analyze_project_structure(project_files)

async def process_git_repo(git_url: str, 
                         branch: str = "main",
                         credentials: Optional[Dict[str, str]] = None,
                         hints: Optional[Dict[str, Any]] = None) -> ProjectFiles:
    """Process Git repository"""
    handler = FileHandler()
    git_info = GitRepositoryInfo(url=git_url, branch=branch, credentials=credentials)
    project_files = await handler.process_git_repository(git_info, hints)
    return await handler.analyze_project_structure(project_files)

async def process_file_dict(files: Dict[str, str], 
                          hints: Optional[Dict[str, Any]] = None) -> ProjectFiles:
    """Process dictionary of files"""
    handler = FileHandler()
    project_files = await handler.process_local_files(files, hints)
    return await handler.analyze_project_structure(project_files) 