"""
Agentic scan pipeline: ordered stages (AST heuristics → Pyre → Pysa) for MCP agent code.
All server-side scanning flows through this module.
"""
from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.utils.file_utils import save_report
from app.utils.pyre_utils import run_pyre, run_pysa
from constants.app_constants import (
    ISSUE_TYPE_MCP,
    PROJECT_ROOT,
    REPORTS_DIR,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from scanner.project_scanner import ProjectScanner

logger = logging.getLogger(__name__)


def _mcp_issues_from_project_scan(upload_root: str, project_id: str) -> list[dict[str, Any]]:
    scanner = ProjectScanner()
    result = scanner.scan_project(upload_root, project_id)
    issues: list[dict[str, Any]] = []
    for fr in result.files:
        for v in fr.vulnerabilities:
            issues.append(
                {
                    "file": fr.relative_path.replace("\\", "/"),
                    "line": v.line,
                    "type": ISSUE_TYPE_MCP,
                    "rule": v.rule,
                    "severity": v.severity,
                    "description": v.description,
                    "fix": v.fix,
                }
            )
    return issues


def run_agentic_scan(upload_folder: str, project_id: str) -> dict[str, Any]:
    """
    Run the full static-analysis pipeline on one extracted upload directory.

    Stages:
      1. mcp_ast — pattern-based rules for MCP tools (fast, no Pyre binary).
      2. pyre — optional type checking (needs pyre.bin).
      3. pysa — optional taint analysis (needs pyre.bin + models in pysa_rules/).
    """
    stages: dict[str, Any] = {}
    started_at = time.perf_counter()
    logger.info("Starting scan pipeline for project %s in %s", project_id, upload_folder)

    mcp_started = time.perf_counter()
    logger.info("Stage mcp_ast started for project %s", project_id)
    mcp_issues = _mcp_issues_from_project_scan(upload_folder, project_id)
    stages["mcp_ast"] = {
        "status": "ok",
        "issue_count": len(mcp_issues),
        "duration_seconds": round(time.perf_counter() - mcp_started, 2),
    }
    logger.info(
        "Stage mcp_ast finished for project %s with %d issues in %.2fs",
        project_id,
        len(mcp_issues),
        stages["mcp_ast"]["duration_seconds"],
    )

    # Run Pyre + Pysa in parallel to reduce API wait time.
    pyre_started = time.perf_counter()
    pysa_started = time.perf_counter()
    logger.info("Stages pyre+pysa started in parallel for project %s", project_id)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            pyre_future = executor.submit(run_pyre, upload_folder)
            pysa_future = executor.submit(run_pysa, upload_folder, project_id)
            pyre_issues, pyre_debug = pyre_future.result()
            pysa_issues, pysa_debug = pysa_future.result()
    except Exception as exc:
        logger.exception("Parallel pyre/pysa execution failed for project %s", project_id)
        pyre_issues, pyre_debug = [], {"pyre_error": str(exc)}
        pysa_issues, pysa_debug = [], {"pysa_error": str(exc)}

    if pyre_debug.get("pyre_skipped"):
        pyre_status = "skipped"
    elif pyre_debug.get("pyre_timeout"):
        pyre_status = "failed"
    elif pyre_debug.get("pyre_returncode") in (0, 1):
        pyre_status = "completed"
    else:
        pyre_status = "failed"
    stages["pyre"] = {
        "status": pyre_status,
        "issue_count": len(pyre_issues),
        "duration_seconds": round(time.perf_counter() - pyre_started, 2),
        "debug": {
            k: v
            for k, v in pyre_debug.items()
            if k
            in (
                "pyre_returncode",
                "pyre_skipped",
                "pyre_timeout",
                "reason",
                "pyre_cwd",
                "pyre_workspace",
                "pyre_stdout",
                "pyre_stderr",
                "pyre_error",
                "bash_cmd",
            )
        },
    }

    if pysa_debug.get("pysa_skipped"):
        pysa_status = "skipped"
    elif pysa_debug.get("pysa_returncode") == 0:
        pysa_status = "completed"
    else:
        pysa_status = "failed"
    stages["pysa"] = {
        "status": pysa_status,
        "issue_count": len(pysa_issues),
        "duration_seconds": round(time.perf_counter() - pysa_started, 2),
        "debug": {
            k: v
            for k, v in pysa_debug.items()
            if k
            in (
                "pysa_returncode",
                "pysa_skipped",
                "pysa_timeout",
                "reason",
                "pysa_cwd",
                "pysa_output_dir",
                "pysa_workspace",
                "pysa_stdout",
                "pysa_stderr",
                "pysa_error",
                "bash_cmd",
            )
        },
    }

    all_issues = mcp_issues + pyre_issues + pysa_issues

    summary = {
        "total": len(all_issues),
        "high": sum(1 for x in all_issues if x.get("severity") == SEVERITY_HIGH),
        "medium": sum(1 for x in all_issues if x.get("severity") == SEVERITY_MEDIUM),
        "low": sum(1 for x in all_issues if x.get("severity") == SEVERITY_LOW),
        "pyre_issues": len(pyre_issues),
        "pysa_issues": len(pysa_issues),
        "mcp_issues": len(mcp_issues),
    }

    debug = {
        **pyre_debug,
        **pysa_debug,
        "project_root": str(PROJECT_ROOT),
        "upload_folder": upload_folder,
        "pipeline_stages": stages,
        "note": "Running all 3 stages: MCP AST + Pyre + Pysa (auto environment mode)",
        "duration_seconds": round(time.perf_counter() - started_at, 2),
    }

    payload = {
        "project_id": project_id,
        "issues": all_issues,
        "summary": summary,
        "pipeline": stages,
        "debug": debug,
    }
    save_report(REPORTS_DIR, project_id, payload)

    return {
        "project_id": project_id,
        "issues_count": len(all_issues),
        "issues_details": all_issues,
        "summary": summary,
        "pipeline": stages,
        "debug": debug,
    }
