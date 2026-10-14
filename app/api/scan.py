import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.analyzer.scan_pipeline import run_agentic_scan
from app.utils.file_utils import create_project_folder, create_project_from_zip
from app.utils.github_utils import get_github_repo
from constants.app_constants import BENCHMARKS_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


class CodeRequest(BaseModel):
    """Request model for scanning code."""
    filename: str
    code: str


class GitHubRequest(BaseModel):
    """Request model for scanning GitHub repository."""
    url: str
    github_token: Optional[str] = None


@router.post("/scan_model")
def scan_model(request: CodeRequest):
    logger.info("Scan request: %s", request.filename)

    project_id, upload_folder, _file_path = create_project_folder(
        BENCHMARKS_DIR, request.filename, request.code
    )

    return run_agentic_scan(upload_folder, project_id)


@router.post("/scan_project")
def scan_project(request: CodeRequest):
    """
    Upload one file but run multi-file pipeline (Pyre/Pysa on folder + project AST walk).
    Same as /scan_model for a single file; use /scan_zip for archives.
    """
    return scan_model(request)


@router.post("/scan_zip")
async def scan_zip(file: UploadFile = File(...)):
    logger.info("ZIP scan request received: filename=%s content_type=%s", file.filename, file.content_type)
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="A .zip file is required.")

    logger.info("Reading ZIP upload into memory for scan")
    content = await file.read()
    logger.info("ZIP upload read complete: %d bytes", len(content))
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="ZIP file is too large (max 25 MB).")

    try:
        logger.info("Extracting ZIP into benchmark folder")
        project_id, upload_folder = create_project_from_zip(BENCHMARKS_DIR, content)
        logger.info("ZIP extracted for project %s at %s", project_id, upload_folder)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    logger.info("Starting analysis pipeline for project %s", project_id)
    return run_agentic_scan(upload_folder, project_id)


@router.post("/scan_github")
def scan_github(request: GitHubRequest):
    """
    Scan a GitHub repository for vulnerabilities.
    Downloads the repository and runs full security analysis pipeline.
    
    Supports:
    - Public repositories
    - Private repositories (with GitHub token)
    - Shallow clone for performance
    """
    logger.info("GitHub scan request: %s", request.url)
    
    try:
        import uuid
        project_id = str(uuid.uuid4())
        upload_folder = f"{BENCHMARKS_DIR}/{project_id}"
        
        # Download GitHub repository
        success, message, repo_path = get_github_repo(
            request.url,
            upload_folder,
            github_token=request.github_token,
            prefer_zip=True
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to download repository: {message}")
        
        logger.info("GitHub repository downloaded: %s", repo_path)
        
        # Run security analysis on downloaded repository
        return run_agentic_scan(upload_folder, project_id)
    
    except Exception as e:
        logger.error("GitHub scan error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Scan error: {str(e)}") from e


@router.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns scanner status and available features.
    """
    return {
        "status": "healthy",
        "service": "MCP Taint Analyzer",
        "endpoints": {
            "scan_model": "POST - Scan single Python file",
            "scan_zip": "POST - Scan ZIP archive",
            "scan_github": "POST - Scan GitHub repository",
            "scan_benchmark/{agent_name}": "GET - Scan benchmark agent",
            "scan_all_benchmarks": "GET - Scan all 4 benchmark agents",
            "health": "GET - Health check",
        },
        "benchmark_agents": [
            "web_scraper",
            "database_query",
            "filesystem",
            "process_execution",
        ],
    }
