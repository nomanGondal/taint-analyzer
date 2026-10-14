import os
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.analyzer.mcp_ast_scanner import MCPASTSCANNER, Vulnerability

logger = logging.getLogger(__name__)


@dataclass
class FileResult:
    file_path: str
    relative_path: str
    vulnerabilities: list = field(default_factory=list)
    error: str | None = None

    def to_dict(self):
        return {
            "file_path": self.relative_path,
            "vulnerabilities": [asdict(v) for v in self.vulnerabilities],
            "error": self.error,
        }


@dataclass
class ProjectScanResult:
    project_id: str
    total_files_scanned: int
    total_vulnerabilities: int
    severity_summary: dict
    files: list[FileResult]

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "total_files_scanned": self.total_files_scanned,
            "total_vulnerabilities": self.total_vulnerabilities,
            "severity_summary": self.severity_summary,
            "files": [f.to_dict() for f in self.files],
        }


class ProjectScanner:
    """
    Walks an entire project directory and runs all scanners
    on every .py file found.
    """

    SKIP_DIRS = {
        "__pycache__", ".git", ".venv", "venv", "env",
        "node_modules", ".mypy_cache", ".pytest_cache", "dist", "build",
    }

    def __init__(self):
        self.ast_scanner = MCPASTSCANNER()

    def scan_project(self, project_root: str, project_id: str) -> ProjectScanResult:
        root = Path(project_root).resolve()
        py_files = list(self._walk_python_files(root))
        logger.info("Found %d Python files in %s", len(py_files), root)

        file_results = []
        for py_file in py_files:
            result = self._scan_file(py_file, root)
            file_results.append(result)

        # Build severity summary
        severity_summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_vulns = 0
        for fr in file_results:
            for vuln in fr.vulnerabilities:
                severity_summary[vuln.severity] = (
                    severity_summary.get(vuln.severity, 0) + 1
                )
                total_vulns += 1

        # Sort: files with HIGH vulns first
        file_results.sort(
            key=lambda r: (
                -sum(1 for v in r.vulnerabilities if v.severity == "HIGH"),
                -len(r.vulnerabilities),
            )
        )

        return ProjectScanResult(
            project_id=project_id,
            total_files_scanned=len(py_files),
            total_vulnerabilities=total_vulns,
            severity_summary=severity_summary,
            files=file_results,
        )

    def _walk_python_files(self, root: Path):
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune dirs we should skip (modifies in-place to stop os.walk descending)
            dirnames[:] = [
                d for d in dirnames if d not in self.SKIP_DIRS
            ]
            for filename in filenames:
                if filename.endswith(".py"):
                    yield Path(dirpath) / filename

    def _scan_file(self, file_path: Path, root: Path) -> FileResult:
        relative = str(file_path.relative_to(root))
        try:
            code = file_path.read_text(encoding="utf-8", errors="replace")
            vulns = self.ast_scanner.scan(code)
            return FileResult(
                file_path=str(file_path),
                relative_path=relative,
                vulnerabilities=vulns,
            )
        except Exception as e:
            logger.error("Error scanning %s: %s", file_path, e)
            return FileResult(
                file_path=str(file_path),
                relative_path=relative,
                error=str(e),
            )