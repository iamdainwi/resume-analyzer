"""
FastAPI application entry point.
Stateless version for Vercel serverless functions.
"""

import logging
import os
import shutil
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import (
    CORS_ORIGINS, UPLOAD_DIR, MAX_UPLOAD_FILES,
    ALLOWED_EXTENSIONS, LOG_LEVEL, IS_VERCEL,
)
from app.job_service import process_job


# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


# ── Lifespan (must be defined before app) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    yield
    logger.info("Shutting down.")


# ── App creation ───────────────────────────────────────────────────────────
app = FastAPI(
    title="HR Resume Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Global error handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def catch_all(request, exc):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "internal server error", "detail": str(exc)},
    )


# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"message": "HR Resume Analyzer API", "status": "running"}


@app.post("/start-job")
async def start_job(
    jd: str = Form(...),
    files: list[UploadFile] = File(...),
):
    if not jd.strip():
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
                detail=f"{f.filename} unsupported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    if IS_VERCEL:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    job_id = int(time.time())
    file_paths = []

    try:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f"{job_id}_{f.filename}")
            with open(path, "wb") as buf:
                shutil.copyfileobj(f.file, buf)
            file_paths.append(path)
            logger.info("Saved file: %s -> %s", f.filename, path)
    except Exception:
        for saved in file_paths:
            if os.path.exists(saved):
                os.remove(saved)
        logger.exception("Failed to save uploaded files")
        raise HTTPException(status_code=500, detail="Failed to save uploaded files")

    results = process_job(jd, file_paths)

    return {
        "job_id": job_id,
        "message": "Processing complete",
        "total_files": len(files),
        **results,
    }
