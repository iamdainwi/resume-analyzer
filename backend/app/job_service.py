"""
Background job processing – scores each resume file against the JD.
"""

import logging
import os
import time
import traceback

from .resume_parser import extract_text, extract_name_from_text, extract_contact_info
from .llm_service import score_resume
from .utils import timing_decorator, log_performance_metrics

logger = logging.getLogger(__name__)


@timing_decorator
def process_job(jd: str, file_paths: list[str]) -> dict:
    """
    Process all uploaded resume files for a given job.
    Returns a dict with processing statistics and list of candidates.
    """
    successful = 0
    failed = 0
    candidates = []

    for i, path in enumerate(file_paths, 1):
        file_start = time.time()
        try:
            logger.info("Processing file %d/%d: %s", i, len(file_paths), os.path.basename(path))

            text = extract_text(path)

            if not text or not text.strip():
                logger.warning("No text extracted from %s", path)
                candidate = {
                    "name": "Unknown",
                    "email": None,
                    "phone": None,
                    "github": None,
                    "score": 0,
                    "classification": "Weak",
                    "summary": "No text extracted",
                }
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

                candidate = {
                    "name": extracted_name or result.get("name", "Unknown"),
                    "email": contact.get("email"),
                    "phone": contact.get("phone"),
                    "github": contact.get("github"),
                    "score": result.get("score", 50),
                    "classification": result.get("classification", "Partial"),
                    "summary": result.get("summary", ""),
                }

            candidates.append(candidate)
            successful += 1
            logger.info("Successfully processed: %s", os.path.basename(path))

        except Exception as e:
            failed += 1
            logger.error("Error processing %s: %s", path, e)
            logger.debug(traceback.format_exc())
            candidates.append({
                "name": "Processing Error",
                "email": None,
                "phone": None,
                "github": None,
                "score": 0,
                "classification": "Weak",
                "summary": f"Failed to process file: {str(e)[:100]}",
            })

        log_performance_metrics(f"File {i} processing", time.time() - file_start)

    # Cleanup files immediately after processing
    _cleanup_files(file_paths)

    # Sort candidates by score descending
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    status = "completed"
    if failed == len(file_paths):
        status = "failed"
    elif failed > 0:
        status = "completed_with_errors"

    return {
        "status": status,
        "processed": successful,
        "total": len(file_paths),
        "candidates": candidates,
    }


def _cleanup_files(paths: list[str]) -> None:
    """Remove uploaded files after processing."""
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info("Cleaned up: %s", path)
        except OSError:
            logger.exception("Failed to clean up %s", path)
