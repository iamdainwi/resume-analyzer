"""
Background job processing – scores each resume file against the JD.
"""

import logging
import os
import time
import traceback

from .database import SessionLocal
from .models import Candidate, Job
from .resume_parser import extract_text, extract_name_from_text, extract_contact_info
from .llm_service import score_resume
from .utils import timing_decorator, log_performance_metrics

logger = logging.getLogger(__name__)


@timing_decorator
def process_job(job_id: int, jd: str, file_paths: list[str]) -> None:
    """
    Process all uploaded resume files for a given job.

    Runs in a background task, so it manages its own DB session
    (cannot use the request-scoped Depends(get_db) here).
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job %d not found", job_id)
            return

        successful = 0
        failed = 0

        for i, path in enumerate(file_paths, 1):
            file_start = time.time()
            try:
                logger.info("Processing file %d/%d: %s", i, len(file_paths), os.path.basename(path))

                text = extract_text(path)

                if not text or not text.strip():
                    logger.warning("No text extracted from %s", path)
                    candidate = Candidate(
                        job_id=job_id, name="Unknown",
                        score=0, classification="Weak",
                        summary="No text extracted",
                    )
                else:
                    # Extract name and contact info with dedicated parser
                    extracted_name = extract_name_from_text(text)
                    contact = extract_contact_info(text)

                    llm_start = time.time()
                    result = score_resume(jd, text)
                    log_performance_metrics(
                        f"LLM scoring for {os.path.basename(path)}",
                        time.time() - llm_start,
                    )

                    candidate = Candidate(
                        job_id=job_id,
                        name=extracted_name or result.get("name", "Unknown"),
                        email=contact.get("email"),
                        phone=contact.get("phone"),
                        github=contact.get("github"),
                        score=result.get("score", 50),
                        classification=result.get("classification", "Partial"),
                        summary=result.get("summary", ""),
                    )

                db.add(candidate)
                successful += 1
                logger.info("Successfully processed: %s", os.path.basename(path))

            except Exception as e:
                failed += 1
                logger.error("Error processing %s: %s", path, e)
                logger.debug(traceback.format_exc())
                try:
                    db.add(Candidate(
                        job_id=job_id, name="Processing Error",
                        score=0, classification="Weak",
                        summary=f"Failed to process file: {str(e)[:100]}",
                    ))
                except Exception:
                    logger.exception("Failed to add error record")
                    db.rollback()

            # Update progress after each file
            job.processed_files = i
            db.commit()
            log_performance_metrics(f"File {i} processing", time.time() - file_start)

        # ── Final status ────────────────────────────────────────────────
        if failed == 0:
            job.status = "completed"
            logger.info("Job %d completed. %d files processed.", job_id, successful)
        elif successful > 0:
            job.status = "completed_with_errors"
            logger.info("Job %d completed with %d ok / %d failed.", job_id, successful, failed)
        else:
            job.status = "failed"
            logger.error("Job %d failed. All %d files failed.", job_id, failed)

        db.commit()
        _cleanup_files(file_paths)

    except Exception:
        logger.exception("Fatal error in process_job %d", job_id)
        try:
            if job:
                job.status = "failed"
                db.commit()
        except Exception:
            logger.exception("Could not mark job as failed")
    finally:
        db.close()


def _cleanup_files(paths: list[str]) -> None:
    """Remove uploaded files after processing."""
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info("Cleaned up: %s", path)
        except OSError:
            logger.exception("Failed to clean up %s", path)
