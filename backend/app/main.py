"""
FastAPI application entry point.

Supports both local (background tasks) and Vercel serverless (synchronous) modes.
On Vercel, BackgroundTasks won't survive past the response, so processing
runs synchronously within the request and returns results directly.
"""

import logging
import os
import shutil
import time

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from .config import (
    CORS_ORIGINS, UPLOAD_DIR, MAX_UPLOAD_FILES, ALLOWED_EXTENSIONS,
    LOG_LEVEL, IS_VERCEL,
)
from .database import Base, engine, get_db
from .models import Job, Candidate
from .job_service import process_job

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


# ── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook."""
    logger.info("Creating database tables...")
    start = time.time()
    Base.metadata.create_all(bind=engine)
    logger.info("Database setup completed in %.2fs", time.time() - start)
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
    background_tasks: BackgroundTasks,
    jd: str = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
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

    # ── Ensure tables + upload dir exist (Vercel cold start) ────────────
    if IS_VERCEL:
        Base.metadata.create_all(bind=engine)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    # ── Create job record ───────────────────────────────────────────────
    job = Job(status="processing", total_files=len(files), processed_files=0)
    db.add(job)
    db.commit()
    db.refresh(job)

    # ── Save uploaded files ─────────────────────────────────────────────
    file_paths: list[str] = []
    try:
        for f in files:
            path = os.path.join(UPLOAD_DIR, f"{job.id}_{int(time.time())}_{f.filename}")
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

    # ── Process ─────────────────────────────────────────────────────────
    if IS_VERCEL:
        # Serverless: run synchronously — background tasks won't survive
        process_job(job.id, jd, file_paths)

        # Re-fetch job and candidates to return full results immediately
        db.refresh(job)
        candidates = (
            db.query(Candidate)
            .filter(Candidate.job_id == job.id)
            .order_by(Candidate.score.desc())
            .all()
        )
        return {
            "job_id": job.id,
            "message": "Processing complete",
            "total_files": len(files),
            "status": job.status,
            "processed": job.processed_files,
            "total": job.total_files,
            "candidates": [
                {
                    "name": c.name,
                    "email": c.email,
                    "phone": c.phone,
                    "github": c.github,
                    "score": round(c.score, 1),
                    "classification": c.classification,
                    "summary": c.summary,
                }
                for c in candidates
            ],
        }
    else:
        # Local: run in background for better UX
        background_tasks.add_task(process_job, job.id, jd, file_paths)
        logger.info("Started job %d with %d files", job.id, len(files))
        return {
            "job_id": job.id,
            "message": "Processing started",
            "total_files": len(files),
        }


@app.get("/job-status/{job_id}")
def job_status(job_id: int, db: Session = Depends(get_db)):
    if job_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = (
        db.query(Candidate)
        .filter(Candidate.job_id == job_id)
        .order_by(Candidate.score.desc())
        .all()
    )

    return {
        "status": job.status,
        "processed": job.processed_files,
        "total": job.total_files,
        "candidates": [
            {
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "github": c.github,
                "score": round(c.score, 1),
                "classification": c.classification,
                "summary": c.summary,
            }
            for c in candidates
        ],
    }
