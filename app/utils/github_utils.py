"""
GitHub Repository Downloader
Provides utilities to download and extract GitHub repositories for scanning.
Supports both public and private repositories with authentication.
"""

import os
import logging
import subprocess
import shutil
import zipfile
import io
import re
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


def parse_github_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse GitHub URL and extract owner, repo, and branch.
    
    Supported formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/branch
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    
    Returns:
        Tuple of (owner, repo, branch) or (None, None, None) if invalid
    """
    # Handle git@ URLs
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/").replace(".git", "")
    
    # Parse URL
    if not ("github.com" in url):
        return None, None, None
    
    # Extract path component
    match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git|/tree/([^/]+)|$)', url)
    if not match:
        return None, None, None
    
    owner = match.group(1)
    repo = match.group(2)
    branch = match.group(3) or "main"
    
    return owner, repo, branch


def download_github_repo(
    url: str,
    target_dir: str,
    github_token: Optional[str] = None,
    timeout: int = 30,
    max_size: int = 100 * 1024 * 1024,  # 100 MB
) -> Tuple[bool, str, str]:
    """
    Download a GitHub repository as ZIP and extract it.
    
    Args:
        url: GitHub repository URL
        target_dir: Directory to extract repository into
        github_token: Optional GitHub API token for authentication
        timeout: Download timeout in seconds
        max_size: Maximum allowed download size in bytes
    
    Returns:
        Tuple of (success: bool, message: str, extracted_path: str)
    """
    owner, repo, branch = parse_github_url(url)
    
    if not owner or not repo:
        return False, "Invalid GitHub URL format", ""
    
    try:
        # Build download URL for ZIP archive
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        
        logger.info(f"Downloading {owner}/{repo} branch {branch} from {zip_url}")
        
        # Create request with headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Download the ZIP file
        req = urllib.request.Request(zip_url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > max_size:
                    return False, f"Repository too large (>{max_size/1024/1024:.0f}MB)", ""
                
                zip_data = response.read()
                
                if len(zip_data) > max_size:
                    return False, f"Downloaded size exceeds limit (>{max_size/1024/1024:.0f}MB)", ""
        
        except urllib.error.URLError as e:
            return False, f"Download failed: {str(e)}", ""
        
        # Extract ZIP to target directory
        os.makedirs(target_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # ZIP structure is: {repo}-{branch}/...
                # We want to extract contents directly to target_dir
                extracted_subdir = f"{repo}-{branch}"
                
                for info in zf.infolist():
                    # Skip the top-level directory
                    if info.filename == extracted_subdir + "/" or info.is_dir():
                        continue
                    
                    # Strip the top-level directory from paths
                    if info.filename.startswith(extracted_subdir + "/"):
                        relative_path = info.filename[len(extracted_subdir) + 1:]
                    else:
                        relative_path = info.filename
                    
                    if not relative_path:
                        continue
                    
                    target_path = os.path.join(target_dir, relative_path)
                    
                    # Prevent zip slip
                    target_path_abs = os.path.abspath(target_path)
                    target_dir_abs = os.path.abspath(target_dir)
                    if not target_path_abs.startswith(target_dir_abs):
                        logger.warning(f"Skipping unsafe path: {relative_path}")
                        continue
                    
                    if info.is_dir():
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with zf.open(info) as source, open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                
                logger.info(f"Repository extracted to {target_dir}")
                return True, "Repository downloaded and extracted successfully", target_dir
        
        except zipfile.BadZipFile:
            return False, "Failed to extract ZIP file - corrupted or invalid format", ""
    
    except Exception as e:
        logger.error(f"Error downloading GitHub repository: {str(e)}")
        return False, f"Error: {str(e)}", ""


def clone_github_repo(
    url: str,
    target_dir: str,
    github_token: Optional[str] = None,
    depth: int = 1,  # Shallow clone by default
) -> Tuple[bool, str, str]:
    """
    Clone a GitHub repository using git (requires git to be installed).
    
    Args:
        url: GitHub repository URL
        target_dir: Directory to clone repository into
        github_token: Optional GitHub API token for authentication
        depth: Depth for shallow clone (use 0 for full clone)
    
    Returns:
        Tuple of (success: bool, message: str, cloned_path: str)
    """
    # Check if git is available
    if not shutil.which("git"):
        logger.warning("Git not found, using ZIP download instead")
        return download_github_repo(url, target_dir, github_token)
    
    try:
        owner, repo, branch = parse_github_url(url)
        
        if not owner or not repo:
            return False, "Invalid GitHub URL format", ""
        
        os.makedirs(target_dir, exist_ok=True)
        
        # Build clone URL with authentication
        if github_token:
            clone_url = f"https://{github_token}@github.com/{owner}/{repo}.git"
        else:
            clone_url = f"https://github.com/{owner}/{repo}.git"
        
        # Prepare clone command
        cmd = ["git", "clone"]
        
        if depth > 0:
            cmd.extend(["--depth", str(depth)])
        
        if branch != "main":
            cmd.extend(["-b", branch])
        
        cmd.extend([clone_url, target_dir])
        
        logger.info(f"Cloning {owner}/{repo} from {clone_url}")
        
        # Execute clone
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info(f"Repository cloned to {target_dir}")
            return True, "Repository cloned successfully", target_dir
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return False, f"Clone failed: {error_msg}", ""
    
    except subprocess.TimeoutExpired:
        return False, "Clone operation timed out", ""
    except Exception as e:
        logger.error(f"Error cloning GitHub repository: {str(e)}")
        return False, f"Error: {str(e)}", ""


def get_github_repo(
    url: str,
    target_dir: str,
    github_token: Optional[str] = None,
    prefer_zip: bool = True,
) -> Tuple[bool, str, str]:
    """
    Download or clone a GitHub repository.
    
    Attempts ZIP download by default, falls back to git clone if available.
    
    Args:
        url: GitHub repository URL
        target_dir: Directory to extract/clone repository into
        github_token: Optional GitHub API token
        prefer_zip: If True, prefer ZIP download over git clone
    
    Returns:
        Tuple of (success: bool, message: str, path: str)
    """
    if prefer_zip:
        success, msg, path = download_github_repo(url, target_dir, github_token)
        if success:
            return success, msg, path
        # Fall back to clone
        logger.info("ZIP download failed, attempting git clone")
        return clone_github_repo(url, target_dir, github_token)
    else:
        success, msg, path = clone_github_repo(url, target_dir, github_token)
        if success:
            return success, msg, path
        # Fall back to download
        logger.info("Git clone failed, attempting ZIP download")
        return download_github_repo(url, target_dir, github_token)
