#!/usr/bin/env python3
"""
Test Agent - Receives code from Code Agent and runs tests.
Subscribes to: tasks.coding
Publishes to: tasks.testing
"""

import asyncio
import os
import json
import logging
import time
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import the existing messaging infrastructure
import sys
sys.path.append('/app')
from src.common.messaging import create_messaging_client, MessagingClient
from src.common.config import Settings

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("test-agent")

# Prometheus metrics
MESSAGES_RECEIVED = Counter('test_messages_received_total', 'Total messages received from coding topic')
MESSAGES_PUBLISHED = Counter('test_messages_published_total', 'Total messages published to testing topic')
TEST_DURATION = Histogram('test_execution_duration_seconds', 'Time spent running tests')
ACTIVE_TEST_RUNS = Gauge('test_active_runs', 'Number of test runs currently being processed')
TEST_ERRORS = Counter('test_errors_total', 'Total test execution errors')
TEST_FAILURES = Counter('test_failures_total', 'Total test failures')
TEST_PASSES = Counter('test_passes_total', 'Total test passes')

# Configuration
SUBSCRIBE_TOPIC = os.getenv("SUBSCRIBE_TOPIC", "tasks.coding")
PUBLISH_TOPIC = os.getenv("PUBLISH_TOPIC", "tasks.testing")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class CodeArtifact(BaseModel):
    """Code artifact from code agent"""
    file_path: str
    content: str
    language: str
    module: str
    dependencies: List[str] = []

class CodeInput(BaseModel):
    """Code from code agent"""
    code_id: str
    blueprint_id: str
    artifacts: List[CodeArtifact]
    test_files: List[CodeArtifact]
    static_analysis_results: Dict[str, Any]
    build_instructions: Dict[str, Any]
    metadata: Dict[str, Any] = {}

class TestResult(BaseModel):
    """Individual test result"""
    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    error_message: Optional[str] = None
    file_path: str

class CoverageReport(BaseModel):
    """Code coverage report"""
    total_lines: int
    covered_lines: int
    coverage_percentage: float
    uncovered_files: List[str]
    detailed_coverage: Dict[str, Dict[str, Any]]

class QualityMetrics(BaseModel):
    """Code quality metrics"""
    complexity_score: float
    maintainability_index: float
    technical_debt_ratio: float
    code_smells: int
    security_hotspots: int
    duplicated_lines: int

class TestOutput(BaseModel):
    """Test execution result to publish"""
    test_id: str
    code_id: str
    test_results: List[TestResult]
    coverage_report: CoverageReport
    quality_metrics: QualityMetrics
    performance_benchmarks: Dict[str, Any]
    security_scan_results: Dict[str, Any]
    overall_status: str  # "passed", "failed", "warning"
    recommendations: List[str]
    metadata: Dict[str, Any]

class TestAgent:
    """
    Test Agent that runs tests and generates quality reports
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
    async def start(self):
        """Initialize the messaging client and start listening"""
        logger.info("Starting Test Agent...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        # Subscribe to coding topic
        self.messaging_client.subscribe(
            topic=SUBSCRIBE_TOPIC,
            callback=self.process_code_message,
            group_id="test-agent-group"
        )
        
        self.is_running = True
        logger.info(f"Test Agent started, subscribed to {SUBSCRIBE_TOPIC}")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping Test Agent...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        logger.info("Test Agent stopped")
        
    async def process_code_message(self, message: Dict[str, Any]):
        """Process a message from the coding topic"""
        start_time = time.time()
        
        try:
            MESSAGES_RECEIVED.inc()
            ACTIVE_TEST_RUNS.inc()
            
            logger.info(f"Received code message: {message}")
            
            # Parse the code from code agent
            code_input = CodeInput(**message)
            
            # Run tests and generate reports
            test_output = await self.run_tests(code_input)
            
            # Publish the test results
            await self.publish_test_results(test_output)
            
            duration = time.time() - start_time
            TEST_DURATION.observe(duration)
            
            logger.info(f"Successfully processed test run {test_output.test_id} in {duration:.2f}s")
            
        except Exception as e:
            TEST_ERRORS.inc()
            logger.error(f"Error processing code message: {e}", exc_info=True)
            raise
        finally:
            ACTIVE_TEST_RUNS.dec()
            
    async def run_tests(self, code_input: CodeInput) -> TestOutput:
        """Run tests on the provided code"""
        
        # Generate unique test ID
        test_id = f"test_{int(time.time())}_{code_input.code_id}"
        
        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write code artifacts to temporary directory
            await self.write_code_to_disk(code_input, temp_path)
            
            # Run different types of tests
            test_results = await self.execute_tests(code_input, temp_path)
            coverage_report = await self.generate_coverage_report(code_input, temp_path)
            quality_metrics = await self.analyze_code_quality(code_input, temp_path)
            performance_benchmarks = await self.run_performance_tests(code_input, temp_path)
            security_scan_results = await self.run_security_scan(code_input, temp_path)
            
            # Determine overall status
            overall_status = self.determine_overall_status(test_results, coverage_report, quality_metrics)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(test_results, coverage_report, quality_metrics)
            
            return TestOutput(
                test_id=test_id,
                code_id=code_input.code_id,
                test_results=test_results,
                coverage_report=coverage_report,
                quality_metrics=quality_metrics,
                performance_benchmarks=performance_benchmarks,
                security_scan_results=security_scan_results,
                overall_status=overall_status,
                recommendations=recommendations,
                metadata={
                    **code_input.metadata,
                    "created_at": time.time(),
                    "agent": "test-agent",
                    "version": "1.0",
                    "test_duration": time.time() - time.time()
                }
            )
            
    async def write_code_to_disk(self, code_input: CodeInput, base_path: Path):
        """Write code artifacts to disk for testing"""
        
        # Write main code files
        for artifact in code_input.artifacts:
            file_path = base_path / artifact.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(artifact.content)
                
        # Write test files
        for test_file in code_input.test_files:
            file_path = base_path / test_file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(test_file.content)
                
        # Create requirements.txt if not exists
        requirements_path = base_path / "requirements.txt"
        if not requirements_path.exists():
            # Extract dependencies from artifacts
            all_deps = set()
            for artifact in code_input.artifacts + code_input.test_files:
                all_deps.update(artifact.dependencies)
                
            with open(requirements_path, 'w') as f:
                for dep in sorted(all_deps):
                    f.write(f"{dep}\n")
                    
    async def execute_tests(self, code_input: CodeInput, base_path: Path) -> List[TestResult]:
        """Execute tests and collect results"""
        test_results = []
        
        # Find test files
        test_files = [artifact for artifact in code_input.test_files if artifact.file_path.startswith("tests/")]
        
        if not test_files:
            # No tests found, create a placeholder result
            test_results.append(TestResult(
                test_name="test_placeholder",
                status="skipped",
                duration=0.0,
                error_message="No tests found",
                file_path="tests/"
            ))
            return test_results
            
        # Run pytest for Python tests
        python_test_files = [tf for tf in test_files if tf.language == "python"]
        
        if python_test_files:
            try:
                # Install dependencies first
                await self.install_dependencies(base_path)
                
                # Run pytest
                start_time = time.time()
                result = subprocess.run(
                    ["python", "-m", "pytest", "tests/", "-v", "--json-report", "--json-report-file=test_results.json"],
                    cwd=base_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    TEST_PASSES.inc()
                    # Parse pytest results
                    results_file = base_path / "test_results.json"
                    if results_file.exists():
                        with open(results_file) as f:
                            pytest_results = json.load(f)
                            test_results.extend(self.parse_pytest_results(pytest_results))
                    else:
                        test_results.append(TestResult(
                            test_name="pytest_run",
                            status="passed", 
                            duration=duration,
                            file_path="tests/"
                        ))
                else:
                    TEST_FAILURES.inc()
                    test_results.append(TestResult(
                        test_name="pytest_run",
                        status="failed",
                        duration=duration,
                        error_message=result.stderr,
                        file_path="tests/"
                    ))
                    
            except subprocess.TimeoutExpired:
                test_results.append(TestResult(
                    test_name="pytest_run",
                    status="error",
                    duration=300.0,
                    error_message="Test execution timed out",
                    file_path="tests/"
                ))
            except Exception as e:
                test_results.append(TestResult(
                    test_name="pytest_run",
                    status="error",
                    duration=0.0,
                    error_message=str(e),
                    file_path="tests/"
                ))
                
        return test_results
        
    async def install_dependencies(self, base_path: Path):
        """Install Python dependencies"""
        requirements_file = base_path / "requirements.txt"
        if requirements_file.exists():
            result = subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=base_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                logger.warning(f"Failed to install dependencies: {result.stderr}")
                
    def parse_pytest_results(self, pytest_results: Dict[str, Any]) -> List[TestResult]:
        """Parse pytest JSON results"""
        test_results = []
        
        tests = pytest_results.get("tests", [])
        for test in tests:
            test_results.append(TestResult(
                test_name=test.get("nodeid", "unknown"),
                status=test.get("outcome", "unknown"),
                duration=test.get("duration", 0.0),
                error_message=test.get("call", {}).get("longrepr") if test.get("outcome") == "failed" else None,
                file_path=test.get("file", "unknown")
            ))
            
        return test_results
        
    async def generate_coverage_report(self, code_input: CodeInput, base_path: Path) -> CoverageReport:
        """Generate code coverage report"""
        
        try:
            # Run coverage analysis
            result = subprocess.run(
                ["python", "-m", "coverage", "run", "-m", "pytest", "tests/"],
                cwd=base_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # Get coverage report
                coverage_result = subprocess.run(
                    ["python", "-m", "coverage", "report", "--format=json"],
                    cwd=base_path,
                    capture_output=True,
                    text=True
                )
                
                if coverage_result.returncode == 0:
                    coverage_data = json.loads(coverage_result.stdout)
                    
                    total_lines = coverage_data.get("totals", {}).get("num_statements", 0)
                    covered_lines = coverage_data.get("totals", {}).get("covered_lines", 0)
                    coverage_percentage = coverage_data.get("totals", {}).get("percent_covered", 0.0)
                    
                    uncovered_files = []
                    detailed_coverage = {}
                    
                    for file_path, file_data in coverage_data.get("files", {}).items():
                        file_coverage = file_data.get("summary", {}).get("percent_covered", 0.0)
                        if file_coverage < 80:  # Below 80% coverage
                            uncovered_files.append(file_path)
                            
                        detailed_coverage[file_path] = {
                            "lines": file_data.get("summary", {}).get("num_statements", 0),
                            "covered": file_data.get("summary", {}).get("covered_lines", 0),
                            "percentage": file_coverage
                        }
                        
                    return CoverageReport(
                        total_lines=total_lines,
                        covered_lines=covered_lines,
                        coverage_percentage=coverage_percentage,
                        uncovered_files=uncovered_files,
                        detailed_coverage=detailed_coverage
                    )
                    
        except Exception as e:
            logger.warning(f"Failed to generate coverage report: {e}")
            
        # Return default coverage report if analysis fails
        return CoverageReport(
            total_lines=0,
            covered_lines=0,
            coverage_percentage=0.0,
            uncovered_files=[],
            detailed_coverage={}
        )
        
    async def analyze_code_quality(self, code_input: CodeInput, base_path: Path) -> QualityMetrics:
        """Analyze code quality metrics"""
        
        # Simple static analysis using basic metrics
        complexity_score = 0.0
        total_files = 0
        total_lines = 0
        
        for artifact in code_input.artifacts:
            if artifact.language == "python":
                total_files += 1
                lines = artifact.content.split('\n')
                total_lines += len(lines)
                
                # Simple complexity calculation based on control structures
                complexity = 1  # Base complexity
                for line in lines:
                    line = line.strip()
                    if any(keyword in line for keyword in ['if', 'elif', 'for', 'while', 'try', 'except']):
                        complexity += 1
                    if any(keyword in line for keyword in ['and', 'or']):
                        complexity += 0.5
                        
                complexity_score += complexity
                
        # Calculate averages
        avg_complexity = complexity_score / total_files if total_files > 0 else 1.0
        
        # Maintainability index (simplified calculation)
        maintainability = max(0, 171 - 5.2 * avg_complexity - 0.23 * (total_lines / total_files if total_files > 0 else 0))
        
        # Technical debt ratio (simplified)
        technical_debt = min(100, avg_complexity * 2)
        
        return QualityMetrics(
            complexity_score=avg_complexity,
            maintainability_index=maintainability,
            technical_debt_ratio=technical_debt,
            code_smells=max(0, int(avg_complexity - 5)),
            security_hotspots=0,  # Would need proper static analysis tool
            duplicated_lines=0   # Would need proper analysis
        )
        
    async def run_performance_tests(self, code_input: CodeInput, base_path: Path) -> Dict[str, Any]:
        """Run performance benchmarks"""
        
        # Basic performance metrics
        performance_metrics = {
            "startup_time": 0.0,
            "memory_usage": 0,
            "response_times": {},
            "throughput": 0,
            "load_test_results": {}
        }
        
        # For now, return simulated performance metrics
        # In a real implementation, you would run actual performance tests
        performance_metrics.update({
            "startup_time": 2.5,  # seconds
            "memory_usage": 128,  # MB
            "response_times": {
                "average": 50,  # ms
                "p95": 100,
                "p99": 200
            },
            "throughput": 1000,  # requests per second
            "load_test_results": {
                "concurrent_users": 100,
                "duration": "1m",
                "success_rate": 99.5
            }
        })
        
        return performance_metrics
        
    async def run_security_scan(self, code_input: CodeInput, base_path: Path) -> Dict[str, Any]:
        """Run security vulnerability scan"""
        
        security_results = {
            "vulnerabilities": [],
            "security_score": 0,
            "recommendations": []
        }
        
        # Basic security checks on code content
        high_risk_patterns = [
            "eval(",
            "exec(",
            "os.system(",
            "subprocess.call(",
            "shell=True",
            "input(",
            "raw_input("
        ]
        
        medium_risk_patterns = [
            "pickle.loads(",
            "yaml.load(",
            "jsonpickle.decode(",
            "requests.get(",
            "urllib.request."
        ]
        
        vulnerabilities = []
        
        for artifact in code_input.artifacts:
            if artifact.language == "python":
                content = artifact.content.lower()
                
                for pattern in high_risk_patterns:
                    if pattern in content:
                        vulnerabilities.append({
                            "severity": "high",
                            "pattern": pattern,
                            "file": artifact.file_path,
                            "description": f"Potentially dangerous function: {pattern}"
                        })
                        
                for pattern in medium_risk_patterns:
                    if pattern in content:
                        vulnerabilities.append({
                            "severity": "medium",
                            "pattern": pattern,
                            "file": artifact.file_path,
                            "description": f"Potentially risky function: {pattern}"
                        })
                        
        # Calculate security score
        high_count = len([v for v in vulnerabilities if v["severity"] == "high"])
        medium_count = len([v for v in vulnerabilities if v["severity"] == "medium"])
        
        security_score = max(0, 100 - (high_count * 20) - (medium_count * 5))
        
        security_results.update({
            "vulnerabilities": vulnerabilities,
            "security_score": security_score,
            "recommendations": [
                "Review and validate all user inputs",
                "Use parameterized queries for database operations",
                "Implement proper authentication and authorization",
                "Enable HTTPS for all communications",
                "Keep dependencies up to date"
            ]
        })
        
        return security_results
        
    def determine_overall_status(self, test_results: List[TestResult], coverage_report: CoverageReport, quality_metrics: QualityMetrics) -> str:
        """Determine overall test status"""
        
        # Check test results
        failed_tests = [tr for tr in test_results if tr.status in ["failed", "error"]]
        if failed_tests:
            return "failed"
            
        # Check coverage
        if coverage_report.coverage_percentage < 50:
            return "warning"
            
        # Check quality metrics
        if quality_metrics.complexity_score > 20 or quality_metrics.maintainability_index < 50:
            return "warning"
            
        return "passed"
        
    def generate_recommendations(self, test_results: List[TestResult], coverage_report: CoverageReport, quality_metrics: QualityMetrics) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Test coverage recommendations
        if coverage_report.coverage_percentage < 80:
            recommendations.append(f"Increase test coverage from {coverage_report.coverage_percentage:.1f}% to at least 80%")
            
        if coverage_report.uncovered_files:
            recommendations.append(f"Add tests for {len(coverage_report.uncovered_files)} uncovered files")
            
        # Code quality recommendations
        if quality_metrics.complexity_score > 10:
            recommendations.append(f"Reduce code complexity (current: {quality_metrics.complexity_score:.1f})")
            
        if quality_metrics.maintainability_index < 70:
            recommendations.append(f"Improve maintainability index (current: {quality_metrics.maintainability_index:.1f})")
            
        # Test failure recommendations
        failed_tests = [tr for tr in test_results if tr.status in ["failed", "error"]]
        if failed_tests:
            recommendations.append(f"Fix {len(failed_tests)} failing tests")
            
        # Performance recommendations
        recommendations.extend([
            "Add performance tests for critical paths",
            "Monitor memory usage in production",
            "Implement caching for frequently accessed data"
        ])
        
        return recommendations
        
    async def publish_test_results(self, test_output: TestOutput):
        """Publish the test results to the testing topic"""
        try:
            message = test_output.dict()
            await self.messaging_client.publish(PUBLISH_TOPIC, message)
            MESSAGES_PUBLISHED.inc()
            logger.info(f"Published test results {test_output.test_id} to {PUBLISH_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to publish test results {test_output.test_id}: {e}")
            raise

# Global agent instance
test_agent = TestAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the agent lifecycle"""
    await test_agent.start()
    yield
    await test_agent.stop()

# FastAPI app
app = FastAPI(
    title="Test Agent", 
    description="Runs tests and generates quality reports for code artifacts",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "test-agent",
        "is_running": test_agent.is_running,
        "subscribe_topic": SUBSCRIBE_TOPIC,
        "publish_topic": PUBLISH_TOPIC
    }

@app.get("/health/liveness")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@app.get("/health/readiness") 
async def readiness():
    """Kubernetes readiness probe"""
    is_ready = test_agent.is_running and test_agent.messaging_client is not None
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/status")
async def status():
    """Get current agent status"""
    return {
        "agent": "test-agent",
        "is_running": test_agent.is_running,
        "topics": {
            "subscribe": SUBSCRIBE_TOPIC,
            "publish": PUBLISH_TOPIC
        },
        "metrics": {
            "messages_received": MESSAGES_RECEIVED._value.get(),
            "messages_published": MESSAGES_PUBLISHED._value.get(),
            "active_runs": ACTIVE_TEST_RUNS._value.get(),
            "errors": TEST_ERRORS._value.get(),
            "failures": TEST_FAILURES._value.get(),
            "passes": TEST_PASSES._value.get()
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        log_level=LOG_LEVEL.lower(),
        reload=False
    ) 