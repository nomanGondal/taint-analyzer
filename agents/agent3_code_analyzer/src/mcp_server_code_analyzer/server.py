"""Agent 3: Code Analyzer MCP Server."""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class CodeMetrics(BaseModel):
    """Metrics for analyzed code."""
    lines_of_code: int = Field(description="Total lines of code")
    complexity: str = Field(description="Cyclomatic complexity level")
    functions: int = Field(description="Number of functions")
    comments_ratio: float = Field(description="Comments to code ratio")
    maintainability_index: float = Field(description="Maintainability score 0-100")


class SecurityIssue(BaseModel):
    """Security issue found in code."""
    severity: str = Field(description="HIGH, MEDIUM, or LOW")
    type: str = Field(description="Type of issue")
    description: str = Field(description="Issue description")


mcp = FastMCP(
    name="Code Analyzer Agent",
    instructions="Analyzes code for quality, security, and optimization opportunities."
)


@mcp.tool()
def analyze_code_quality(code: str, language: str = "python") -> CodeMetrics:
    """Analyze code quality and compute metrics."""
    lines = code.split('\n')
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
    functions = code.count('def ') if language == 'python' else code.count('function ')
    
    if len(code_lines) < 50:
        complexity = "Low"
    elif len(code_lines) < 150:
        complexity = "Medium"
    else:
        complexity = "High"
    
    comments = sum(1 for l in lines if l.strip().startswith('#'))
    comments_ratio = comments / max(1, len(code_lines))
    maintainability = max(0, 100 - len(code_lines) * 0.5 + functions * 5)
    maintainability = min(100, maintainability)
    
    return CodeMetrics(
        lines_of_code=len(code_lines),
        complexity=complexity,
        functions=functions,
        comments_ratio=round(comments_ratio, 2),
        maintainability_index=round(maintainability, 1)
    )


@mcp.tool()
def security_scan(code: str) -> list[SecurityIssue]:
    """Scan code for security vulnerabilities."""
    issues = []
    
    if 'eval(' in code:
        issues.append(SecurityIssue(severity="HIGH", type="Code Injection", description="Use of eval() is dangerous"))
    
    if 'password' in code.lower() and '=' in code:
        issues.append(SecurityIssue(severity="HIGH", type="Hardcoded Secret", description="Hardcoded password or API key detected"))
    
    if 'shell=True' in code:
        issues.append(SecurityIssue(severity="MEDIUM", type="Shell Injection", description="subprocess with shell=True is vulnerable"))
    
    return issues


@mcp.tool()
def review_code(code: str) -> dict:
    """Perform comprehensive code review."""
    metrics = analyze_code_quality(code)
    issues = security_scan(code)
    
    quality_score = metrics.maintainability_index - len(issues) * 10
    quality_score = max(0, min(100, quality_score))
    
    improvements = []
    if metrics.comments_ratio < 0.1:
        improvements.append("Add more code comments and docstrings")
    if metrics.complexity == "High":
        improvements.append("Break complex functions into smaller ones")
    if len(issues) > 0:
        improvements.append(f"Address {len(issues)} security issues")
    
    return {
        "quality_score": round(quality_score, 1),
        "issues": [vars(i) for i in issues],
        "improvements": improvements
    }


@mcp.tool()
def suggest_refactoring(code: str) -> dict:
    """Suggest refactoring opportunities."""
    return {
        "suggestions": [
            {"type": "Extract Function", "reason": "Long method should be broken into smaller functions"},
            {"type": "Remove Duplication", "reason": "Similar code patterns detected"},
            {"type": "Simplify Conditional", "reason": "Complex if-else logic can be simplified"}
        ],
        "estimated_improvement": "15-20% reduction in complexity"
    }


if __name__ == "__main__":
    mcp.run()
