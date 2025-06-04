# Adding Existing Codebase Support to Multi-Agent Pipeline

## Overview

This document outlines the implementation plan for extending the multi-agent pipeline to work with existing codebases rather than just generating projects from scratch. This would significantly expand the system's usefulness for real-world scenarios.

## Implementation Phases

### **Phase 1: Basic Existing Codebase Support** 
**Difficulty: 🟡 Medium (2-3 weeks)**
**Immediate Value: High**

#### 1.1 API Gateway Enhancements

**Extend ProjectRequest Model:**
```python
class ProjectRequest(BaseModel):
    """Enhanced project request with existing codebase support"""
    project_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10, max_length=5000)
    requirements: List[str] = Field(default_factory=list, max_items=50)
    constraints: List[str] = Field(default_factory=list, max_items=20)
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    deadline: Optional[str] = None
    technology_preferences: List[str] = Field(default_factory=list, max_items=10)
    
    # NEW: Existing codebase fields
    project_type: str = Field(default="new", pattern="^(new|existing|fork)$")
    existing_codebase: Optional[ExistingCodebase] = None
    modification_scope: Optional[str] = Field(default="feature", pattern="^(feature|refactor|migration|enhancement)$")
    
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExistingCodebase(BaseModel):
    """Configuration for existing codebase"""
    source_type: str = Field(..., pattern="^(git_url|file_upload|git_server)$")
    
    # Git repository options
    git_url: Optional[str] = None
    git_branch: Optional[str] = "main"
    git_credentials: Optional[Dict[str, str]] = None
    
    # File upload options
    uploaded_files: Optional[Dict[str, str]] = None  # filename -> content
    
    # Project context
    main_language: Optional[str] = None
    framework: Optional[str] = None
    project_structure: Optional[str] = None  # "monorepo", "microservices", "standard"
    
    # Analysis hints
    entry_points: List[str] = Field(default_factory=list)  # main files to analyze
    ignore_patterns: List[str] = Field(default_factory=list)  # files/dirs to ignore
    important_directories: List[str] = Field(default_factory=list)  # key dirs to focus on
```

**Enhanced Web Dashboard:**
```html
<!-- Add to the dashboard form -->
<div class="form-group">
    <label for="projectType">Project Type:</label>
    <select id="projectType" name="projectType" onchange="toggleCodebaseSection()">
        <option value="new" selected>New Project</option>
        <option value="existing">Existing Codebase</option>
        <option value="fork">Fork Existing Project</option>
    </select>
</div>

<div id="existingCodebaseSection" style="display: none;">
    <div class="form-group">
        <label for="sourceType">Source Type:</label>
        <select id="sourceType" name="sourceType">
            <option value="git_url">Git Repository URL</option>
            <option value="file_upload">Upload Files (ZIP)</option>
            <option value="git_server">Internal Git Server</option>
        </select>
    </div>
    
    <div class="form-group" id="gitUrlSection">
        <label for="gitUrl">Repository URL:</label>
        <input type="url" id="gitUrl" name="gitUrl" 
               placeholder="https://github.com/user/repo.git">
        <label for="gitBranch">Branch:</label>
        <input type="text" id="gitBranch" name="gitBranch" value="main">
    </div>
    
    <div class="form-group">
        <label for="modificationScope">Modification Scope:</label>
        <select id="modificationScope" name="modificationScope">
            <option value="feature" selected>Add New Feature</option>
            <option value="enhancement">Enhance Existing Feature</option>
            <option value="refactor">Refactor/Improve Code</option>
            <option value="migration">Technology Migration</option>
        </select>
    </div>
    
    <div class="form-group">
        <label for="mainLanguage">Main Language (if known):</label>
        <input type="text" id="mainLanguage" name="mainLanguage" 
               placeholder="Python, JavaScript, Java, etc.">
    </div>
    
    <div class="form-group">
        <label for="framework">Framework (if known):</label>
        <input type="text" id="framework" name="framework" 
               placeholder="FastAPI, React, Django, etc.">
    </div>
</div>
```

#### 1.2 Enhanced Analysis Agent

**Codebase Analysis Capabilities:**
```python
class CodebaseAnalyzer:
    """Analyzes existing codebases to understand structure and architecture"""
    
    def __init__(self):
        self.supported_languages = ["python", "javascript", "typescript", "java", "go", "rust"]
        self.file_analyzers = {
            "python": PythonAnalyzer(),
            "javascript": JavaScriptAnalyzer(),
            "typescript": TypeScriptAnalyzer(),
            # ... more analyzers
        }
    
    async def analyze_codebase(self, codebase_path: Path, hints: Dict[str, Any]) -> CodebaseAnalysis:
        """Analyze an existing codebase"""
        
        analysis = CodebaseAnalysis(
            path=str(codebase_path),
            detected_language=await self.detect_primary_language(codebase_path),
            detected_framework=await self.detect_framework(codebase_path),
            project_structure=await self.analyze_structure(codebase_path),
            dependencies=await self.extract_dependencies(codebase_path),
            api_endpoints=await self.find_api_endpoints(codebase_path),
            database_models=await self.find_database_models(codebase_path),
            test_files=await self.find_test_files(codebase_path),
            deployment_configs=await self.find_deployment_configs(codebase_path),
            code_metrics=await self.calculate_metrics(codebase_path),
            integration_points=await self.identify_integration_points(codebase_path)
        )
        
        return analysis

class CodebaseAnalysis(BaseModel):
    """Results of codebase analysis"""
    path: str
    detected_language: str
    detected_framework: Optional[str]
    project_structure: ProjectStructure
    dependencies: List[Dependency]
    api_endpoints: List[APIEndpoint]
    database_models: List[DatabaseModel]
    test_files: List[str]
    deployment_configs: List[str]
    code_metrics: CodeMetrics
    integration_points: List[IntegrationPoint]
    recommendations: List[str]

class ProjectStructure(BaseModel):
    """Project structure analysis"""
    type: str  # "monorepo", "microservices", "standard", "unknown"
    main_directories: List[str]
    source_directories: List[str]
    test_directories: List[str]
    config_files: List[str]
    entry_points: List[str]
    documentation_files: List[str]

class IntegrationPoint(BaseModel):
    """Points where new code can integrate with existing code"""
    type: str  # "api_endpoint", "database_model", "service_class", "utility_function"
    location: str  # file path and line number
    name: str
    description: str
    parameters: List[str]
    example_usage: Optional[str]
```

**Enhanced Analysis Process:**
```python
async def analyze_requirements_with_codebase(self, 
                                           requirements: List[str], 
                                           codebase_analysis: Optional[CodebaseAnalysis]) -> AnalysisResult:
    """Enhanced analysis that considers existing codebase"""
    
    if codebase_analysis:
        # Modify analysis to consider existing architecture
        existing_patterns = self.extract_architectural_patterns(codebase_analysis)
        integration_strategy = self.plan_integration_strategy(requirements, codebase_analysis)
        modification_tasks = self.identify_modification_tasks(requirements, codebase_analysis)
        
        return AnalysisResult(
            intent=self.extract_intent(requirements),
            existing_codebase_summary=codebase_analysis,
            integration_strategy=integration_strategy,
            tasks=modification_tasks,
            architectural_constraints=existing_patterns,
            compatibility_notes=self.check_compatibility(requirements, codebase_analysis),
            recommended_approach=self.recommend_implementation_approach(requirements, codebase_analysis)
        )
    else:
        # Original greenfield analysis
        return await self.analyze_requirements(requirements)
```

#### 1.3 Enhanced Planning Agent

**Integration-Aware Planning:**
```python
class IntegrationPlan(BaseModel):
    """Plan for integrating new features with existing codebase"""
    modification_strategy: str  # "extend", "refactor", "replace", "add_alongside"
    files_to_modify: List[FileModification]
    files_to_create: List[str]
    integration_points: List[str]
    testing_strategy: TestingStrategy
    rollback_plan: str
    compatibility_requirements: List[str]

class FileModification(BaseModel):
    """Specific file modification plan"""
    file_path: str
    modification_type: str  # "add_function", "modify_class", "add_import", "refactor"
    target_location: Optional[str]  # where in file to make changes
    description: str
    impact_assessment: str  # "low", "medium", "high"
    backup_required: bool = True

async def plan_integration_project(self, 
                                 analysis_result: AnalysisResult) -> IntegrationPlan:
    """Plan how to integrate new features with existing codebase"""
    
    codebase = analysis_result.existing_codebase_summary
    requirements = analysis_result.tasks
    
    # Determine modification strategy
    strategy = self.determine_modification_strategy(requirements, codebase)
    
    # Plan specific file modifications
    file_mods = self.plan_file_modifications(requirements, codebase, strategy)
    
    # Plan new files needed
    new_files = self.plan_new_files(requirements, codebase, strategy)
    
    # Testing strategy for existing + new code
    testing = self.plan_integration_testing(codebase, file_mods, new_files)
    
    return IntegrationPlan(
        modification_strategy=strategy,
        files_to_modify=file_mods,
        files_to_create=new_files,
        integration_points=analysis_result.integration_strategy,
        testing_strategy=testing,
        rollback_plan=self.create_rollback_plan(file_mods),
        compatibility_requirements=analysis_result.compatibility_notes
    )
```

#### 1.4 Enhanced Code Agent

**Code Modification Capabilities:**
```python
class CodeModifier:
    """Handles modification of existing code files"""
    
    async def modify_file(self, 
                         file_path: str, 
                         file_content: str,
                         modification: FileModification) -> str:
        """Modify an existing file based on modification plan"""
        
        if modification.modification_type == "add_function":
            return self.add_function_to_file(file_content, modification)
        elif modification.modification_type == "modify_class":
            return self.modify_class_in_file(file_content, modification)
        elif modification.modification_type == "add_import":
            return self.add_import_to_file(file_content, modification)
        elif modification.modification_type == "refactor":
            return self.refactor_file_section(file_content, modification)
        else:
            raise ValueError(f"Unknown modification type: {modification.modification_type}")
    
    def add_function_to_file(self, content: str, modification: FileModification) -> str:
        """Add a new function to an existing file"""
        lines = content.split('\n')
        
        # Find the best location to add the function
        insertion_point = self.find_function_insertion_point(lines, modification.target_location)
        
        # Generate the new function code
        new_function = self.generate_function_code(modification)
        
        # Insert the function
        lines.insert(insertion_point, new_function)
        
        return '\n'.join(lines)
    
    def modify_class_in_file(self, content: str, modification: FileModification) -> str:
        """Modify an existing class in a file"""
        # Parse the file to find the class
        tree = ast.parse(content)
        
        # Find the target class and modify it
        modified_tree = self.modify_ast_class(tree, modification)
        
        # Convert back to source code
        return ast.unparse(modified_tree)
```

#### 1.5 Enhanced Test & Deploy Agent

**Integration Testing:**
```python
async def test_integration_project(self, 
                                 code_input: CodeInput,
                                 original_codebase: Optional[Path]) -> TestOutput:
    """Test both new code and integration with existing codebase"""
    
    if original_codebase:
        # Run existing tests first to ensure no regressions
        existing_test_results = await self.run_existing_tests(original_codebase)
        
        # Run new tests for new functionality
        new_test_results = await self.run_new_tests(code_input)
        
        # Run integration tests
        integration_test_results = await self.run_integration_tests(code_input, original_codebase)
        
        # Combine results
        all_results = existing_test_results + new_test_results + integration_test_results
        
        # Check for regressions
        regression_analysis = await self.analyze_regressions(existing_test_results)
        
    else:
        # Standard new project testing
        all_results = await self.run_tests(code_input)
        regression_analysis = None
    
    return TestOutput(
        test_results=all_results,
        regression_analysis=regression_analysis,
        integration_status="success" if all(r.status == "passed" for r in all_results) else "failed",
        # ... other fields
    )
```

### **Expected Outcomes of Phase 1**

After implementing Phase 1, users would be able to:

1. **Submit existing Git repositories** for enhancement
2. **Get basic analysis** of existing codebase structure
3. **Receive modification plans** that respect existing architecture
4. **Generate code changes** that integrate with existing files
5. **Test both new and existing functionality** to prevent regressions

### **Complexity Assessment**

| Component | Complexity | Time Estimate | Risk Level |
|-----------|------------|---------------|------------|
| API Gateway enhancements | Low | 3 days | Low |
| Basic codebase analysis | Medium | 1 week | Medium |
| Integration planning | Medium | 1 week | Medium |
| Code modification logic | High | 1.5 weeks | High |
| Integration testing | Medium | 4 days | Medium |

**Total: ~5 weeks for a robust Phase 1 implementation**

### **Phase 2 & 3 Previews**

#### **Phase 2: Advanced Codebase Understanding (4-6 weeks)**
- **AST-based code analysis** for deep understanding
- **Dependency graph analysis** for impact assessment
- **Architectural pattern recognition** (MVC, microservices, etc.)
- **Database schema analysis** and migration planning
- **Advanced integration strategies** (event-driven, plugin systems)

#### **Phase 3: Full Integration Platform (2-3 months)**
- **Visual code diff and review** system
- **Automated refactoring** capabilities
- **Database migration** generation and testing
- **Complex deployment scenarios** (blue-green, canary)
- **AI-powered code review** and optimization suggestions

## Implementation Priority

**Recommended approach**: Start with Phase 1 focusing on **Git repository integration** since:

1. **Highest immediate value** - most users have code in Git
2. **Leverages existing infrastructure** - we already have Git server integration
3. **Natural extension** of current artifact persistence
4. **Manageable complexity** for first iteration
5. **Clear path to Phase 2/3** expansion

## Getting Started

The most valuable first step would be:

1. **Extend the ProjectRequest model** to accept Git URLs
2. **Add codebase cloning** to the analysis agent
3. **Implement basic file structure analysis** 
4. **Modify code agent** to handle file modifications vs. creation
5. **Enhance testing** to run existing test suites

This would immediately enable users to point the pipeline at existing repositories and get meaningful enhancements, making the system much more practical for real-world usage.

## Benefits

- **10x expansion** of addressable use cases
- **Real-world applicability** vs. just greenfield projects  
- **Gradual adoption** path for teams with existing codebases
- **Legacy system modernization** capabilities
- **Competitive differentiation** vs. code generation tools 