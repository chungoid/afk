# Local Project Support for Multi-Agent Pipeline

## Overview

Many developers work on local projects that aren't in Git repositories yet. Supporting local project upload would make the pipeline accessible to a much broader audience and handle common real-world scenarios.

## Implementation Options (Ranked by Difficulty)

### **Option 1: ZIP File Upload** 
**Difficulty: 🟢 Easy (1-2 days)**
**Best for: Quick implementation, works with any project size**

#### Enhanced API Gateway with File Upload

```python
import zipfile
import tempfile
from fastapi import UploadFile, File, Form
from pathlib import Path

@app.post("/submit_with_files", response_model=SubmissionResponse)
async def submit_project_with_files(
    project_data: str = Form(...),  # JSON string of ProjectRequest
    project_files: Optional[UploadFile] = File(None)  # ZIP file
):
    """Submit a project with optional file upload"""
    
    try:
        # Parse project data
        request = ProjectRequest.parse_raw(project_data)
        
        # Handle file upload if provided
        uploaded_files = None
        if project_files and request.project_type == "existing_local":
            uploaded_files = await process_uploaded_files(project_files, request)
        
        # Submit with uploaded files
        request_id = await api_gateway.submit_project_with_files(request, uploaded_files)
        
        return SubmissionResponse(
            request_id=request_id,
            status="submitted",
            message=f"Project '{request.project_name}' with files submitted successfully",
            dashboard_url=f"{ORCHESTRATOR_URL}/dashboard",
            api_status_url=f"/status/{request_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit project with files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_uploaded_files(upload_file: UploadFile, request: ProjectRequest) -> Dict[str, str]:
    """Process uploaded ZIP file and extract contents"""
    
    # Validate file
    if not upload_file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    if upload_file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save uploaded file
        zip_path = temp_path / upload_file.filename
        with open(zip_path, "wb") as buffer:
            content = await upload_file.read()
            buffer.write(content)
        
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path / "extracted")
        
        # Read all files (respecting ignore patterns)
        extracted_path = temp_path / "extracted"
        files = {}
        
        for file_path in extracted_path.rglob("*"):
            if file_path.is_file() and not should_ignore_file(file_path, request.ignore_patterns):
                relative_path = file_path.relative_to(extracted_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files[str(relative_path)] = f.read()
                except UnicodeDecodeError:
                    # Skip binary files
                    logger.debug(f"Skipping binary file: {relative_path}")
                    continue
        
        return files

def should_ignore_file(file_path: Path, ignore_patterns: List[str]) -> bool:
    """Check if file should be ignored based on patterns"""
    file_str = str(file_path)
    for pattern in ignore_patterns:
        if pattern in file_str or file_path.name.startswith(pattern):
            return True
    return False
```

#### Enhanced Web Dashboard

```html
<!-- Enhanced form with file upload support -->
<form id="projectForm" enctype="multipart/form-data">
    <!-- Existing fields... -->
    
    <div class="form-group">
        <label for="projectType">Project Type:</label>
        <select id="projectType" name="projectType" onchange="toggleProjectSource()">
            <option value="new" selected>New Project</option>
            <option value="existing_git">Existing Git Repository</option>
            <option value="existing_local">Local Project (Upload Files)</option>
        </select>
    </div>
    
    <!-- Git URL section (existing) -->
    <div id="gitSection" style="display: none;">
        <!-- Git URL fields... -->
    </div>
    
    <!-- Local file upload section -->
    <div id="localSection" style="display: none;">
        <div class="form-group">
            <label for="projectFiles">Project Files (ZIP):</label>
            <input type="file" id="projectFiles" name="projectFiles" accept=".zip">
            <small class="help-text">
                Upload a ZIP file containing your project. Max size: 50MB<br>
                Files matching common ignore patterns (.git, node_modules, etc.) will be skipped.
            </small>
        </div>
        
        <div class="form-group">
            <label for="mainLanguage">Primary Language:</label>
            <select id="mainLanguage" name="mainLanguage">
                <option value="">Auto-detect</option>
                <option value="python">Python</option>
                <option value="javascript">JavaScript/Node.js</option>
                <option value="typescript">TypeScript</option>
                <option value="java">Java</option>
                <option value="go">Go</option>
                <option value="rust">Rust</option>
                <option value="php">PHP</option>
                <option value="csharp">C#</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="framework">Framework (if known):</label>
            <input type="text" id="framework" name="framework" 
                   placeholder="e.g., FastAPI, React, Django, Spring Boot">
        </div>
    </div>
    
    <!-- Existing fields... -->
    
    <button type="submit">🚀 Launch Pipeline</button>
</form>

<script>
function toggleProjectSource() {
    const projectType = document.getElementById('projectType').value;
    const gitSection = document.getElementById('gitSection');
    const localSection = document.getElementById('localSection');
    
    gitSection.style.display = projectType === 'existing_git' ? 'block' : 'none';
    localSection.style.display = projectType === 'existing_local' ? 'block' : 'none';
}

// Enhanced form submission
document.getElementById('projectForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const projectType = formData.get('projectType');
    
    // Build project data
    const projectData = {
        project_name: formData.get('projectName'),
        description: formData.get('description'),
        requirements: formData.get('requirements').split('\n').filter(r => r.trim()),
        project_type: projectType,
        priority: formData.get('priority'),
        technology_preferences: formData.get('technologies').split(',').map(t => t.trim()).filter(t => t)
    };
    
    // Add type-specific fields
    if (projectType === 'existing_git') {
        projectData.git_url = formData.get('gitUrl');
        projectData.git_branch = formData.get('gitBranch') || 'main';
    } else if (projectType === 'existing_local') {
        projectData.main_language = formData.get('mainLanguage');
        projectData.framework = formData.get('framework');
    }
    
    // Prepare submission
    const submitData = new FormData();
    submitData.append('project_data', JSON.stringify(projectData));
    
    // Add files if uploading local project
    if (projectType === 'existing_local' && formData.get('projectFiles')) {
        submitData.append('project_files', formData.get('projectFiles'));
    }
    
    try {
        const endpoint = projectType === 'existing_local' ? '/submit_with_files' : '/submit';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: projectType === 'existing_local' ? submitData : JSON.stringify(projectData),
            headers: projectType !== 'existing_local' ? {'Content-Type': 'application/json'} : undefined
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess(result);
            e.target.reset();
        } else {
            throw new Error(result.detail || 'Submission failed');
        }
    } catch (error) {
        showError(error.message);
    }
});
</script>
```

### **Option 2: Drag & Drop Interface** 
**Difficulty: 🟡 Medium (3-5 days)**
**Best for: Better user experience, handles folders**

```html
<!-- Modern drag & drop interface -->
<div id="dropZone" class="drop-zone" style="display: none;">
    <div class="drop-zone-content">
        <h3>📁 Drop Your Project Here</h3>
        <p>Drag and drop your project folder or select files</p>
        <input type="file" id="fileInput" multiple webkitdirectory style="display: none;">
        <button type="button" onclick="document.getElementById('fileInput').click()">
            📂 Select Project Folder
        </button>
    </div>
    
    <div id="fileList" class="file-list"></div>
</div>

<style>
.drop-zone {
    border: 2px dashed #ccc;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    margin: 20px 0;
    background-color: #f9f9f9;
    transition: all 0.3s ease;
}

.drop-zone.dragover {
    border-color: #007bff;
    background-color: #e3f2fd;
}

.file-list {
    max-height: 200px;
    overflow-y: auto;
    margin-top: 10px;
    text-align: left;
}

.file-item {
    padding: 5px;
    border-bottom: 1px solid #eee;
    font-size: 12px;
}
</style>

<script>
// Drag & drop functionality
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
});

fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
});

function handleFiles(files) {
    // Filter and display files
    const validFiles = files.filter(file => {
        return !shouldIgnoreFile(file.name) && file.size < 5 * 1024 * 1024; // 5MB per file
    });
    
    displayFileList(validFiles);
    
    // Store files for submission
    window.uploadedFiles = validFiles;
}

function shouldIgnoreFile(filename) {
    const ignorePatterns = [
        '.git', 'node_modules', '__pycache__', '.venv', '.env',
        '.pyc', '.log', '.DS_Store', 'dist', 'build'
    ];
    
    return ignorePatterns.some(pattern => filename.includes(pattern));
}

function displayFileList(files) {
    fileList.innerHTML = '';
    
    if (files.length === 0) {
        fileList.innerHTML = '<p>No valid files found</p>';
        return;
    }
    
    files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>${file.webkitRelativePath || file.name}</span>
            <span style="float: right; color: #666;">${formatFileSize(file.size)}</span>
        `;
        fileList.appendChild(fileItem);
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
</script>
```

### **Option 3: Progressive File Upload** 
**Difficulty: 🟡 Medium (1 week)**
**Best for: Large projects, better progress tracking**

```python
# Chunked upload for large projects
from fastapi import WebSocket
import asyncio

@app.websocket("/ws/upload/{request_id}")
async def websocket_upload(websocket: WebSocket, request_id: str):
    """WebSocket endpoint for progressive file upload"""
    await websocket.accept()
    
    project_files = {}
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "file_chunk":
                # Receive file in chunks
                file_path = data["file_path"]
                chunk_data = data["chunk_data"]
                is_last_chunk = data["is_last_chunk"]
                
                if file_path not in project_files:
                    project_files[file_path] = ""
                
                project_files[file_path] += chunk_data
                
                # Send progress update
                await websocket.send_json({
                    "type": "progress",
                    "file_path": file_path,
                    "progress": data["chunk_index"] / data["total_chunks"] * 100
                })
                
                if is_last_chunk:
                    await websocket.send_json({
                        "type": "file_complete",
                        "file_path": file_path
                    })
            
            elif data["type"] == "upload_complete":
                # All files uploaded, start processing
                await websocket.send_json({
                    "type": "processing_started",
                    "message": "Files uploaded successfully, starting analysis..."
                })
                
                # Store files and trigger pipeline
                await store_uploaded_files(request_id, project_files)
                await trigger_analysis_pipeline(request_id)
                
                break
                
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

## **Enhanced Analysis Agent for Local Projects**

```python
class LocalProjectAnalyzer:
    """Analyzes uploaded local projects"""
    
    async def analyze_local_project(self, 
                                  files: Dict[str, str], 
                                  hints: Dict[str, Any]) -> CodebaseAnalysis:
        """Analyze uploaded project files"""
        
        # Detect project structure
        structure = self.detect_project_structure(files)
        
        # Detect language and framework
        language = hints.get("main_language") or self.detect_primary_language(files)
        framework = hints.get("framework") or self.detect_framework(files, language)
        
        # Analyze dependencies
        dependencies = await self.extract_dependencies_from_files(files, language)
        
        # Find key files
        entry_points = self.find_entry_points(files, language, framework)
        api_endpoints = await self.find_api_endpoints_in_files(files, language, framework)
        database_models = await self.find_database_models_in_files(files, language, framework)
        
        # Calculate metrics
        metrics = self.calculate_code_metrics(files)
        
        # Identify integration points
        integration_points = self.identify_integration_points_in_files(files, language, framework)
        
        return CodebaseAnalysis(
            path="uploaded_project",
            detected_language=language,
            detected_framework=framework,
            project_structure=structure,
            dependencies=dependencies,
            api_endpoints=api_endpoints,
            database_models=database_models,
            test_files=self.find_test_files_in_upload(files),
            deployment_configs=self.find_deployment_configs_in_upload(files),
            code_metrics=metrics,
            integration_points=integration_points,
            recommendations=self.generate_recommendations(structure, language, framework)
        )
    
    def detect_project_structure(self, files: Dict[str, str]) -> ProjectStructure:
        """Detect project structure from file paths"""
        file_paths = list(files.keys())
        
        # Analyze directory structure
        directories = set()
        for path in file_paths:
            parts = Path(path).parts[:-1]  # Exclude filename
            for i in range(len(parts)):
                directories.add('/'.join(parts[:i+1]))
        
        # Common patterns
        has_src = any('src' in d for d in directories)
        has_tests = any('test' in d.lower() for d in directories)
        has_docs = any('doc' in d.lower() for d in directories)
        
        # Detect project type
        if 'package.json' in files:
            project_type = "nodejs"
        elif any(f.endswith('.py') for f in file_paths):
            project_type = "python"
        elif any(f.endswith('.java') for f in file_paths):
            project_type = "java"
        else:
            project_type = "unknown"
        
        return ProjectStructure(
            type=project_type,
            main_directories=sorted(directories),
            source_directories=[d for d in directories if 'src' in d or 'lib' in d],
            test_directories=[d for d in directories if 'test' in d.lower()],
            config_files=[f for f in file_paths if self.is_config_file(f)],
            entry_points=self.find_entry_points(files, project_type, None),
            documentation_files=[f for f in file_paths if f.endswith('.md') or 'doc' in f.lower()]
        )
```

## **Enhanced Project Request Model**

```python
class ProjectRequest(BaseModel):
    """Enhanced project request supporting local uploads"""
    project_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10, max_length=5000)
    requirements: List[str] = Field(default_factory=list, max_items=50)
    
    # Project source options
    project_type: str = Field(default="new", pattern="^(new|existing_git|existing_local)$")
    
    # Git repository (existing)
    git_url: Optional[str] = None
    git_branch: Optional[str] = "main"
    
    # Local project hints
    main_language: Optional[str] = None
    framework: Optional[str] = None
    ignore_patterns: List[str] = Field(default_factory=lambda: [
        "node_modules", ".git", "__pycache__", ".venv", ".env", 
        "*.pyc", "*.log", ".DS_Store", "dist", "build"
    ])
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

## **Benefits of Local Project Support**

### **Immediate Benefits**
1. **No Git Required** - Users can get started immediately with any project
2. **Privacy Friendly** - Code never leaves their environment until they choose to upload
3. **Quick Experimentation** - Perfect for testing the pipeline on existing work
4. **Educational Use** - Great for students and learning projects

### **User Experience**
- **Zero Setup** - No need to initialize Git, create repositories, etc.
- **Visual Feedback** - See exactly which files are being analyzed
- **Incremental Adoption** - Try the pipeline without committing to Git workflow

### **Technical Advantages**
- **Simpler Implementation** - No Git authentication, branch handling, etc.
- **Better Control** - Users explicitly choose which files to include
- **Faster Processing** - No cloning delays, immediate file access

## **Combined Approach: Best of Both Worlds**

**Recommended Implementation Order:**
1. **Start with ZIP upload** (1-2 days) - Quick win, covers most use cases
2. **Add Git repository support** (1 week) - Handles version-controlled projects  
3. **Enhance with drag & drop** (3-5 days) - Better UX
4. **Add progressive upload** (1 week) - Handle larger projects

This gives users **maximum flexibility**:
- **Local projects** → ZIP upload or drag & drop
- **Git projects** → Repository URL
- **Mixed workflow** → Start local, move to Git later

The pipeline becomes accessible to **everyone**, regardless of their current development setup! 