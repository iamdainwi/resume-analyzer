"""
LLM-based resume scoring with keyword-based fallback.

Key changes from original:
- Extracted shared `STOP_WORDS` and `extract_keywords()` to eliminate
  duplicated keyword-matching logic between score_resume / fallback.
- Config-driven Ollama settings.
- Cleaner JSON extraction with validation.
"""

import json
import logging
import re
import traceback

from ollama import Client

from .config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_API_KEY, MAX_JD_CHARS, MAX_RESUME_CHARS

logger = logging.getLogger(__name__)

# ── Ollama client ───────────────────────────────────────────────────────────
_headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
client = Client(host=OLLAMA_HOST, headers=_headers)

# ── Shared constants ────────────────────────────────────────────────────────
STOP_WORDS: set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on",
    "at", "to", "for", "of", "with", "by", "is",
    "are", "was", "were", "be", "been", "have",
    "has", "had", "that", "this", "it", "we", "you",
    "they", "will", "can", "should", "must", "not",
    "from", "as", "do", "does", "did", "so", "if",
}

VALID_CLASSIFICATIONS = {"Excellent", "Strong", "Partial", "Weak"}

# ── Shared keyword extraction ──────────────────────────────────────────────

def extract_keywords(text: str) -> set[str]:
    """Return meaningful keywords from text, filtering out stop words."""
    return set(text.lower().split()) - STOP_WORDS


def compute_keyword_match(jd: str, resume_text: str) -> dict:
    """
    Compute keyword overlap between JD and resume.
    Returns dict with matched_keywords, jd_keywords, match_ratio.
    """
    jd_keywords = extract_keywords(jd)
    resume_keywords = extract_keywords(resume_text)
    matches = resume_keywords & jd_keywords

    return {
        "matched_keywords": sorted(matches)[:10],
        "jd_keywords": sorted(jd_keywords)[:10],
        "match_ratio": len(matches) / len(jd_keywords) if jd_keywords else 0,
    }


# ── Name extraction (lightweight, for fallback) ────────────────────────────

_NAME_PATTERNS = [
    re.compile(r'^[A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?'),
    re.compile(r'^[A-Z]\. [A-Z][a-z]+'),
    re.compile(r'^[A-Z][a-z]+, [A-Z]\.'),
    re.compile(r'^[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+'),
]

_SKIP_PHRASES = {
    "email", "phone", "address", "objective",
    "summary", "experience", "education",
    "skills", "resume", "cv",
}


def _extract_name_from_lines(text: str) -> str:
    """Best-effort name extraction from first few lines of resume text."""
    for line in text.split("\n")[:5]:
        line = line.strip()
        if not line or len(line) > 60:
            continue
        if any(phrase in line.lower() for phrase in _SKIP_PHRASES):
            continue
        for pattern in _NAME_PATTERNS:
            match = pattern.match(line)
            if match:
                return match.group(0).title()
    return "Unknown"


# ── Fallback scorer (keyword-based) ────────────────────────────────────────

def fallback_score_resume(jd: str, resume_text: str) -> dict:
    """Score a resume using simple keyword matching when LLM is unavailable."""
    name = _extract_name_from_lines(resume_text)
    kw = compute_keyword_match(jd, resume_text)

    score = min(85, int(kw["match_ratio"] * 100)) if kw["match_ratio"] > 0 else 50

    if score >= 75:
        classification = "Strong"
    elif score >= 60:
        classification = "Partial"
    else:
        classification = "Weak"

    return {
        "name": name,
        "score": score,
        "classification": classification,
        "summary": f"Fallback analysis: {len(kw['matched_keywords'])} keyword matches",
        **kw,
    }


# ── Main LLM scorer ────────────────────────────────────────────────────────

def score_resume(jd: str, resume_text: str) -> dict:
    """Score a resume against a job description using the LLM, with fallback."""

    if not jd.strip():
        return {
            "name": "Unknown", "score": 0,
            "classification": "Partial", "summary": "Invalid job description",
        }

    if not resume_text.strip():
        return {
            "name": "Unknown", "score": 0,
            "classification": "Partial", "summary": "Invalid resume text",
        }

    # Truncate to avoid token overflow
    jd_trimmed = jd[:MAX_JD_CHARS]
    resume_trimmed = resume_text[:MAX_RESUME_CHARS]

    prompt = (
        "Evaluate the resume against the job description.\n\n"
        "Return JSON only in this exact format:\n"
        '{"name": "Name", "score": 0-100, '
        '"classification": "Excellent/Strong/Partial/Weak", '
        '"summary": "Brief summary"}\n\n'
        f"JOB DESCRIPTION:\n{jd_trimmed}\n\n"
        f"RESUME:\n{resume_trimmed}"
    )

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        output = response["message"]["content"]

        # Extract JSON from response
        start = output.find("{")
        end = output.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in LLM response")

        result = json.loads(output[start:end])

        # Validate and clamp fields
        result["name"] = result.get("name", "Unknown") or "Unknown"
        result["score"] = max(0, min(100, float(result.get("score", 50))))
        classification = result.get("classification", "Partial")
        result["classification"] = classification if classification in VALID_CLASSIFICATIONS else "Partial"
        result["summary"] = result.get("summary", "No summary available")

        # Enrich with keyword matching data
        result.update(compute_keyword_match(jd_trimmed, resume_trimmed))

        return result

    except Exception as e:
        logger.error("LLM scoring failed, using fallback: %s", e)
        logger.debug(traceback.format_exc())
        return fallback_score_resume(jd, resume_text)


# ── CLI test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_jd = "Looking for Python developer with FastAPI, SQL, and ML experience."
    sample_resume = (
        "John Doe\n"
        "Experienced Python developer with FastAPI and SQL knowledge.\n"
        "Worked on ML models using scikit-learn."
    )
    print(json.dumps(score_resume(sample_jd, sample_resume), indent=2))
