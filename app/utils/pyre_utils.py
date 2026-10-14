import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.utils.file_utils import _write_pyre_config_for_upload
from constants.app_constants import (
    ISSUE_TYPE_PYRE,
    ISSUE_TYPE_PYSA,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYRE_TIMEOUT_SECONDS = 300
PYSA_TIMEOUT_SECONDS = 300


def _running_inside_wsl_or_linux() -> bool:
    # If app itself is running under Linux/WSL, call pyre directly.
    if os.name != "nt":
        return True
    return False


def _to_wsl_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("C:/", "/mnt/c/")





def _runtime_env_for_pyre() -> dict[str, str]:
    env = dict(os.environ)
    # In Linux/WSL, force pyre client to use a native pyre.bin.
    if _running_inside_wsl_or_linux():
        native_bin = None
        if Path("/usr/local/bin/pyre.bin").is_file():
            native_bin = "/usr/local/bin/pyre.bin"
        if not native_bin:
            candidate = shutil.which("pyre.bin")
            if candidate:
                normalized = candidate.replace("\\", "/")
                if not normalized.endswith("/venv/bin/pyre.bin"):
                    native_bin = candidate
        if native_bin:
            env["PYRE_BINARY"] = native_bin
    return env

def _kill_stale_pyre_server(workspace_root: Path) -> None:
    """Kill any lingering pyre server that may be blocking the socket."""
    try:
        subprocess.run(
            ["pyre", "kill"],
            cwd=str(workspace_root),
            capture_output=True,
            timeout=10,
            env=_runtime_env_for_pyre(),
        )
    except Exception:
        pass  

def _build_pyre_cmd(workspace_root: Path) -> tuple[list[str], str]:
    if _running_inside_wsl_or_linux():
        return (
            ["pyre", "--noninteractive", "check"],
            f"cd '{workspace_root}' && pyre --noninteractive check"
        )
    wsl_cwd = _to_wsl_path(workspace_root)
    bash_cmd = f"cd '{wsl_cwd}' && pyre --noninteractive check"
    return ["wsl", "bash", "-lc", bash_cmd], bash_cmd


def _build_pysa_cmd(workspace_root: Path, out_dir: Path) -> tuple[list[str], str]:
    if _running_inside_wsl_or_linux():
        bash_cmd = (
            f"cd '{workspace_root}' && pyre --noninteractive analyze "
            f"--output-format json --save-results-to '{out_dir}' --no-verify"
        )
        return [
            "pyre", "--noninteractive", "analyze",
            "--output-format", "json",
            "--save-results-to", str(out_dir),
            "--no-verify",
        ], bash_cmd
    wsl_cwd = _to_wsl_path(workspace_root)
    wsl_out_dir = _to_wsl_path(out_dir)
    bash_cmd = (
        f"cd '{wsl_cwd}' && pyre --noninteractive analyze "
        f"--output-format json --save-results-to '{wsl_out_dir}' --no-verify"
    )
    return ["wsl", "bash", "-lc", bash_cmd], bash_cmd


def _prepare_isolated_workspace(cwd_path: Path, stage: str) -> Path:
    scan_id = cwd_path.name
    base_tmp = Path(tempfile.gettempdir()) / "taintAnalyzer_pyre"
    base_tmp.mkdir(parents=True, exist_ok=True)
    workspace_root = Path(
        tempfile.mkdtemp(prefix=f"{scan_id}_{stage}_", dir=str(base_tmp))
    )
    logger.info("Preparing isolated Pyre workspace at %s", workspace_root)
    skip_dirs = {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".pyre",
        "reports",
    }
    keep_suffixes = {".py", ".pyi"}
    max_python_files = 10  # Increased slightly to handle more complex codebases
    mcp_hints = ("mcp", "fastmcp", "@mcp.tool", ".tool(", "resource(", "@resource")
    selected_python_files: list[Path] = []
    fallback_python_files: list[Path] = []

    for root, dirs, files in os.walk(cwd_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        root_path = Path(root)
        for filename in files:
            src = root_path / filename
            if filename == ".pyre_configuration":
                rel = root_path.relative_to(cwd_path)
                target_root = workspace_root / rel
                target_root.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target_root / filename)
                continue
            if src.suffix not in keep_suffixes:
                continue
            if src.suffix == ".pyi":
                rel = root_path.relative_to(cwd_path)
                target_root = workspace_root / rel
                target_root.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target_root / filename)
                continue

            fallback_python_files.append(src)
            try:
                snippet = src.read_text(encoding="utf-8", errors="ignore")[:4000].lower()
            except OSError:
                snippet = ""
            if any(h in snippet for h in mcp_hints):
                selected_python_files.append(src)

    # Focus analysis on MCP-relevant files first to avoid request timeouts.
    # If no MCP-like file is found, keep only a very small fallback set.
    if selected_python_files:
        ordered = selected_python_files
    else:
        ordered = fallback_python_files[:2]
    for src in ordered[:max_python_files]:
        rel = src.parent.relative_to(cwd_path)
        target_root = workspace_root / rel
        target_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target_root / src.name)

    files_copied = min(len(ordered), max_python_files)
    logger.info(
        "Isolated workspace prepared: %d Python files copied (%d selected, %d fallback)",
        files_copied,
        len(selected_python_files),
        len(fallback_python_files),
    )

    # Always refresh generated config to enforce current binary/model paths.
    _write_pyre_config_for_upload(str(workspace_root))
    return workspace_root


def _resolve_pyre_binary() -> str | None:
    """Find pyre.bin in venv/bin (Linux binary, run via WSL)."""
    pyre_bin = _PROJECT_ROOT / "venv" / "bin" / "pyre.bin"
    if pyre_bin.is_file():
        logger.info("Found pyre.bin at %s", pyre_bin)
        return str(pyre_bin)
    logger.warning("pyre.bin not found at %s", pyre_bin)
    return None


def _resolve_pyre_exe() -> str | None:
    """Find pyre.exe wrapper in venv/Scripts."""
    pyre_exe = _PROJECT_ROOT / "venv" / "Scripts" / "pyre.exe"
    if pyre_exe.is_file():
        logger.info("Found pyre.exe at %s", pyre_exe)
        return str(pyre_exe)
    logger.warning("pyre.exe not found at %s", pyre_exe)
    return None


def run_pyre(cwd: str) -> tuple[list, dict]:
    started_at = time.perf_counter()
    cwd_path = Path(cwd)
    if not cwd_path.is_absolute():
        cwd_path = _PROJECT_ROOT / cwd_path
    safe_cwd = str(cwd_path.resolve())
    workspace_root = _prepare_isolated_workspace(cwd_path, "pyre")
    
    _kill_stale_pyre_server(workspace_root)  # ← YE LINE ADD KARO
    
    run_env = _runtime_env_for_pyre()
    cmd, bash_cmd = _build_pyre_cmd(workspace_root)
    run_env = _runtime_env_for_pyre()
    
    # Run pyre in the upload folder so the per-scan .pyre_configuration is used
    cmd, bash_cmd = _build_pyre_cmd(workspace_root)
    
    logger.info("Running Pyre in isolated workspace: %s", " ".join(cmd))
    logger.debug("Pyre timeout: %ds, workspace: %s, cwd: %s", PYRE_TIMEOUT_SECONDS, workspace_root, safe_cwd)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PYRE_TIMEOUT_SECONDS,
            env=run_env,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started_at
        logger.error("Pyre timed out after %.2fs in %s", elapsed, safe_cwd)
        logger.warning(
            "Pyre timeout diagnostic: workspace=%s, files_count=?, check workspace size",
            workspace_root,
        )
        return [], {
            "pyre_returncode": -1,
            "pyre_stdout": (exc.stdout or ""),
            "pyre_stderr": f"Pyre timed out after {PYRE_TIMEOUT_SECONDS}s",
            "pyre_timeout": True,
            "pyre_cwd": safe_cwd,
            "pyre_workspace": str(workspace_root),
            "bash_cmd": bash_cmd,
            "pyre_binary_runtime": run_env.get("PYRE_BINARY"),
        }
    elapsed = time.perf_counter() - started_at

    logger.info(
        "Pyre finished in %.2fs with return code %s (stdout=%d chars, stderr=%d chars)",
        elapsed,
        result.returncode,
        len(result.stdout or ""),
        len(result.stderr or ""),
    )
    if result.stdout:
        logger.info("Pyre stdout preview: %s", (result.stdout[:2000]).replace("\n", " | "))

    if result.stderr:
        logger.info("Pyre stderr: %s", result.stderr)

    issues = _parse_pyre_output(result.stdout)
    logger.info("Pyre found %d issues", len(issues))

    debug = {
        "pyre_returncode": result.returncode,
        "pyre_stdout": result.stdout,
        "pyre_stderr": result.stderr,
        "pyre_cwd": safe_cwd,
        "pyre_workspace": str(workspace_root),
        "bash_cmd": bash_cmd,
        "pyre_binary_runtime": run_env.get("PYRE_BINARY"),
    }
    return issues, debug


def run_pysa(cwd: str, project_id: str) -> tuple[list, dict]:
    """Run pyre analyze (Pysa) via WSL from the extracted upload folder."""
    started_at = time.perf_counter()
    # Resolve path - if relative, make it relative to project root
    cwd_path = Path(cwd)
    if not cwd_path.is_absolute():
        cwd_path = _PROJECT_ROOT / cwd_path
    safe_cwd = str(cwd_path.resolve())
    workspace_root = _prepare_isolated_workspace(cwd_path, "pysa")
    _kill_stale_pyre_server(workspace_root)
    run_env = _runtime_env_for_pyre()
    out_dir = (_PROJECT_ROOT / "reports" / "pysa_runs" / project_id).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Run pyre analyze in the upload folder so the per-scan .pyre_configuration is used
    cmd, bash_cmd = _build_pysa_cmd(workspace_root, out_dir)
    
    logger.info("Running Pysa in isolated workspace: %s", " ".join(cmd))
    logger.debug("Pysa timeout: %ds, workspace: %s, cwd: %s", PYSA_TIMEOUT_SECONDS, workspace_root, safe_cwd)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PYSA_TIMEOUT_SECONDS,
            env=run_env,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started_at
        logger.error("Pysa timed out after %.2fs in %s", elapsed, safe_cwd)
        logger.warning(
            "Pysa timeout diagnostic: workspace=%s, files_count=?, check workspace size",
            workspace_root,
        )
        return [], {
            "pysa_returncode": -1,
            "pysa_stdout": (exc.stdout or ""),
            "pysa_stderr": f"Pysa timed out after {PYSA_TIMEOUT_SECONDS}s",
            "pysa_timeout": True,
            "pysa_cwd": safe_cwd,
            "pysa_workspace": str(workspace_root),
            "pysa_output_dir": str(out_dir),
            "bash_cmd": bash_cmd,
            "pyre_binary_runtime": run_env.get("PYRE_BINARY"),
        }
    elapsed = time.perf_counter() - started_at

    logger.info(
        "Pysa finished in %.2fs with return code %s (stdout=%d chars, stderr=%d chars)",
        elapsed,
        result.returncode,
        len(result.stdout or ""),
        len(result.stderr or ""),
    )
    if result.stdout:
        logger.info("Pysa stdout preview: %s", (result.stdout[:2000]).replace("\n", " | "))

    if result.stderr:
        logger.info("Pysa stderr: %s", result.stderr)

    issues = _load_pysa_issues(out_dir)
    logger.info("Pysa found %d issues", len(issues))

    debug = {
        "pysa_returncode": result.returncode,
        "pysa_stdout": result.stdout,
        "pysa_stderr": result.stderr,
        "pysa_cwd": safe_cwd,
        "pysa_workspace": str(workspace_root),
        "pysa_output_dir": str(out_dir),
        "bash_cmd": bash_cmd,
        "pyre_binary_runtime": run_env.get("PYRE_BINARY"),
    }
    return issues, debug


def _parse_pyre_output(stdout: str) -> list:
    issues = []
    for line in (stdout or "").splitlines():
        stripped = line.strip()
        if not stripped or ".py:" not in stripped:
            continue
        parts = stripped.split(":", 3)
        if len(parts) < 4:
            continue
        path_part, line_part, _col, message_part = parts
        try:
            line_number = int(line_part)
        except ValueError:
            continue

        # Map Pyre error codes to severity
        severity = "medium"
        if any(code in stripped for code in ("[21]", "[16]")):
            severity = "low"       # undefined import/attribute
        elif any(code in stripped for code in ("[29]", "[56]")):
            severity = "high"      # call errors, invalid decorators
        elif any(code in stripped for code in ("[11]", "[58]", "[13]")):
            severity = "medium"    # type annotation errors, unsupported operands

        issues.append(
            {
                "file": path_part.replace("\\", "/"),
                "line": line_number,
                "type": ISSUE_TYPE_PYRE,
                "severity": severity,
                "description": message_part.strip(),
            }
        )
    return issues


def _load_pysa_issues(out_dir: Path) -> list:
    path = out_dir / "taint-output.json"
    if not path.is_file():
        for p in out_dir.glob("*.json"):
            path = p
            break
        else:
            return []
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        logger.warning("Could not read Pysa JSON %s: %s", path, e)
        return []
    
    # Try JSONL format first (one JSON object per line)
    data = []
    for line in content.strip().split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            # Only extract issue records from JSONL
            if isinstance(obj, dict) and obj.get("kind") == "issue":
                data.append(obj.get("data", {}))
        except json.JSONDecodeError:
            pass
    
    # If JSONL parsing didn't work, try standard JSON
    if not data:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Could not parse Pysa JSON %s: %s", path, e)
            return []
    
    return _parse_pysa_json(data)


def _parse_pysa_json(data) -> list:
    if isinstance(data, dict):
        if "errors" in data:
            data = data["errors"]
        elif "issues" in data:
            data = data["issues"]
        elif "results" in data:
            data = data["results"]
        else:
            data = [data]

    if not isinstance(data, list):
        return []

    issues: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        
        # Extract path/filename (Pysa uses "filename" field)
        path = (
            item.get("path")
            or item.get("filename")
            or item.get("file")
        )
        
        # Extract line number
        line = item.get("line") or item.get("line_number")
        
        if path is None or line is None:
            continue
        
        try:
            line_int = int(line)
        except (TypeError, ValueError):
            continue
        
        # Extract name/rule (Pysa uses "code" field for issue code)
        code = item.get("code")
        name = item.get("name") or item.get("rule") or code or "taint_flow"
        
        # Extract description (Pysa uses "message" field)
        desc = (
            item.get("description")
            or item.get("message")
            or item.get("concise_description")
            or item.get("long_description")
            or str(name)
        )
        
        # Add severity based on issue type
        severity = SEVERITY_HIGH if code in (6101, 6102, 6103, 6104, 6105, 6106) else SEVERITY_MEDIUM
        
        issues.append(
            {
                "file": str(path).replace("\\", "/"),
                "line": line_int,
                "type": ISSUE_TYPE_PYSA,
                "rule": str(name),
                "severity": severity,
                "description": str(desc).strip(),
            }
        )
    return issues
