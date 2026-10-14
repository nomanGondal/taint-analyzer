import io
import json
import logging
import os
import uuid
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolved at import: app/utils -> project root (taintAnalyzer)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _select_pyre_binary_for_config() -> str:
    env_binary = os.environ.get("PYRE_BINARY", "").strip()
    candidates: list[str] = []
    if env_binary:
        candidates.append(env_binary)
    # Prefer a known-good Linux binary when running in WSL/Linux.
    candidates.append("/usr/local/bin/pyre.bin")
    # Keep project venv binary as last fallback only.
    candidates.append(str(_PROJECT_ROOT / "venv" / "bin" / "pyre.bin"))

    for raw in candidates:
        if not raw:
            continue
        normalized = raw.replace("\\", "/")
        # Skip known problematic venv pyre.bin paths that cause exec format errors.
        if normalized.endswith("/venv/bin/pyre.bin") and normalized != "/usr/local/bin/pyre.bin":
            continue
        check_path = Path(normalized)
        if normalized.startswith("/") and check_path.is_file():
            return normalized
    return "/usr/local/bin/pyre.bin"


def _to_wsl_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("C:/", "/mnt/c/")


def _write_pyre_config_for_upload(upload_folder: str) -> None:
    upload = Path(upload_folder).resolve()
    stubs_path = _to_wsl_path(_PROJECT_ROOT / "pysa_rules" / "stubs")
    models_path = _to_wsl_path(_PROJECT_ROOT / "pysa_rules")
    
    # Build search path with stdlib + stubs + venv for dependency resolution
    search_paths = [stubs_path]
    for stdlib_path in [
        "/usr/local/lib/python3.11",
        "/usr/lib/python3.11",
        "/usr/local/lib/python3.12",
        "/usr/lib/python3.12",
        "/usr/local/lib/python3.12/dist-packages",
        "/usr/lib/python3/dist-packages",
    ]:
        if Path(stdlib_path).exists():
            search_paths.append(stdlib_path)
    venv_site_packages = _PROJECT_ROOT / "venv" / "lib" / "python3.11" / "site-packages"
    if venv_site_packages.is_dir():
        search_paths.append(_to_wsl_path(venv_site_packages))
        logger.debug("Added venv site-packages to Pyre search path: %s", venv_site_packages)
    
    cfg = {
        # Use "all" strategy to find dependencies in search_path (venv), not system-wide
        "site_package_search_strategy": "all",
        "source_directories": ["."],
        "exclude": [
            r"^\.pyre/.*",
            r"^__pycache__/.*",
            r"^\.venv/.*",
            r"^venv/.*",
            r"^.*/site-packages/.*",
            r"^.*/dist-packages/.*",
            r"^.*/twisted/.*",
            r"^.*/tests?/.*",
        ],
        "search_path": search_paths,
        "taint_models_path": [models_path],
        "strict": False,
        "python_version": "3.11",  # Match project Python version
    }
    pyre_binary = _select_pyre_binary_for_config()
    if pyre_binary:
        cfg["binary"] = pyre_binary.replace("\\", "/").replace("C:/", "/mnt/c/")
    (upload / ".pyre_configuration").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8"
    )
    logger.info("Wrote Pyre config with search paths: %s", search_paths)


def create_project_folder(
    benchmarks_dir: str, filename: str, code: str
) -> tuple[str, str, str]:
    project_id = str(uuid.uuid4())
    upload_folder = f"{benchmarks_dir}/{project_id}"
    os.makedirs(upload_folder, exist_ok=True)
    logger.info("Created folder: %s", upload_folder)

    file_path = os.path.join(upload_folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
    logger.info("Wrote code to: %s", file_path)

    _write_pyre_config_for_upload(upload_folder)
    return project_id, upload_folder, file_path


def create_project_from_zip(
    benchmarks_dir: str, content: bytes, max_uncompressed_bytes: int = 30 * 1024 * 1024
) -> tuple[str, str]:
    project_id = str(uuid.uuid4())
    upload_folder = Path(benchmarks_dir) / project_id
    upload_folder.mkdir(parents=True, exist_ok=True)
    base = upload_folder.resolve()

    total_uncompressed = 0
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        # Get list of files to detect top-level folder (for agent ZIPs)
        file_list = [f for f in zf.namelist() if not f.endswith('/')]
        top_folder = None
        if file_list:
            first_part = file_list[0].split('/')[0]
            if all(f.startswith(first_part + '/') or f == first_part for f in file_list):
                top_folder = first_part

        for info in zf.infolist():
            if info.is_dir():
                continue
            
            name = info.filename.replace("\\", "/")
            
            # Skip top-level folder if all files are under it
            if top_folder and name.startswith(top_folder + '/'):
                name = name[len(top_folder) + 1:]
            
            if not name:
                continue
            
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError(f"Unsafe zip path: {name!r}")
            
            target = (base / name).resolve()
            try:
                target.relative_to(base)
            except ValueError as e:
                raise ValueError(f"Zip slip attempt: {name!r}") from e

            total_uncompressed += info.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise ValueError("ZIP uncompressed size exceeds limit")

            # Create parent directories, removing any files that block the path
            parent = target.parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except (FileExistsError, NotADirectoryError):
                # If parent path exists as file, remove it
                if parent.exists() and parent.is_file():
                    parent.unlink()
                    parent.mkdir(parents=True, exist_ok=True)
                else:
                    # Check all parent levels
                    for p in [parent] + list(parent.parents):
                        if p.exists() and p.is_file():
                            p.unlink()
                    parent.mkdir(parents=True, exist_ok=True)
            
            with zf.open(info, "r") as src, open(target, "wb") as out:
                chunk = src.read(1024 * 1024)
                while chunk:
                    out.write(chunk)
                    chunk = src.read(1024 * 1024)

    upload_str = str(upload_folder)
    _write_pyre_config_for_upload(upload_str)
    logger.info("Extracted ZIP to %s", upload_str)
    return project_id, upload_str


def save_report(reports_dir: str, project_id: str, payload: dict) -> str:
    os.makedirs(reports_dir, exist_ok=True)
    report_path = f"{reports_dir}/{project_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("Saved report: %s", report_path)
    return report_path
