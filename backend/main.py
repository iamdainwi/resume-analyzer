"""
FastAPI application entry point.

Stateless version: No database, no background tasks.
Requests are processed synchronously and results returned immediately.
This is optimal for Vercel serverless functions.
"""

import logging
import os
import shutil
import time

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import (
    CORS_ORIGINS, UPLOAD_DIR, MAX_UPLOAD_FILES, ALLOWED_EXTENSIONS,
    LOG_LEVEL, IS_VERCEL,
)
from .job_service import process_job

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


# ── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="HR Resume Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"message": "HR Resume Analyzer API", "status": "running"}


@app.post("/start-job")
async def start_job(
    jd: str = Form(...),
    files: list[UploadFile] = File(...),
):
    # ── Validate inputs ─────────────────────────────────────────────────
    if not jd or not jd.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")

    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded")

    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_UPLOAD_FILES} files allowed per job",
        )

    for f in files:
        if not f.filename:
            raise HTTPException(status_code=400, detail="All files must have names")
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File {f.filename} has unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    # ── Ensure upload dir exists (Vercel cold start) ────────────────────
    if IS_VERCEL:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    # ── Save uploaded files ─────────────────────────────────────────────
    # We generate a unique ID for this batch just for file organization
    job_id = int(time.time())
    file_paths: list[str] = []
    
    try:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f"{job_id}_{f.filename}")
            with open(path, "wb") as buf:
                shutil.copyfileobj(f.file, buf)
            file_paths.append(path)
            logger.info("Saved file: %s -> %s", f.filename, path)
    except Exception:
        # Roll back saved files on partial failure
        for saved in file_paths:
            if os.path.exists(saved):
                os.remove(saved)
        logger.exception("Failed to save uploaded files")
        raise HTTPException(status_code=500, detail="Failed to save uploaded files")

    # ── Process Synchronously ───────────────────────────────────────────
    # Since we are stateless, we process immediately and return results
    results = process_job(jd, file_paths)

    return {
        "job_id": job_id,
        "message": "Processing complete",
        "total_files": len(files),
        **results  # includes status, processed, candidates
    }
