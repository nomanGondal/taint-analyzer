import logging
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.scan import router as scan_router
from app.utils.pyre_utils import _resolve_pyre_exe
from constants.app_constants import PROJECT_ROOT

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Taint Analyzer",
    description="Static analysis for MCP-based agents (Pyre, Pysa, AST heuristics)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
  allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://mscan.me",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start_pyre() -> None:
    """Pyre is invoked on-demand during scans, no need for persistent server."""
    pyre_exe = _resolve_pyre_exe()
    if pyre_exe:
        logger.info("Pyre executable found at: %s", pyre_exe)
    else:
        logger.warning("Pyre executable not found; scans will be skipped")


app.include_router(scan_router, prefix="/api/v1/scan")


@app.get("/")
def root():
    return {"message": "Server is listening.", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)