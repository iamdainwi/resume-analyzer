"""
Resume text extraction and candidate name detection.

Key changes from original:
- `HEADER_WORDS` extracted to a single module-level constant (was declared 3x).
- Duplicate email extraction (Pattern 5) removed — Pattern 3 already covers it.
- `_is_name_candidate()` helper consolidates the repeated word-count / alpha check.
- Unused `extract_candidate_info()` removed.
"""

import re
from typing import Optional

import pdfplumber
from docx import Document


# ── Shared constants ────────────────────────────────────────────────────────

HEADER_WORDS: set[str] = {
    "resume", "cv", "curriculum", "vitae", "application",
    "profile", "objective", "summary", "professional",
}

NON_NAME_PHRASES: set[str] = {
    "contact information", "professional experience", "education summary",
    "skills overview", "work history", "education", "experience", "skills",
}

SKIP_LINE_WORDS: set[str] = {
    "resume", "cv", "curriculum", "vitae", "experience", "education",
    "skills", "contact", "phone", "email", "address", "linkedin",
    "github", "portfolio", "website", "professional", "summary",
    "objective", "analyst", "developer", "engineer",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _line_is_header(line: str) -> bool:
    """Return True if the line looks like a section header, not a name."""
    return any(hw in line.lower() for hw in HEADER_WORDS)


def _extract_name_words(line: str) -> Optional[str]:
    """
    If `line` looks like a 2-4 word personal name, return the cleaned name.
    Otherwise return None.
    """
    words = line.split()
    if not (2 <= len(words) <= 4) or len(line) >= 50:
        return None

    name_words: list[str] = []
    for word in words:
        clean = re.sub(r'[^\w\s-]', '', word)
        if clean.isalpha() or clean.replace('-', '').isalpha():
            name_words.append(clean)

    return ' '.join(name_words) if len(name_words) >= 2 else None


def _name_from_email(email: str) -> Optional[str]:
    """Attempt to derive a first + last name from an email's local part."""
    local = email.split('@')[0]

    # john.doe@… → John Doe
    if '.' in local:
        parts = [p.capitalize() for p in local.split('.')[:3] if p.isalpha() and len(p) > 1]
        if len(parts) >= 2:
            return ' '.join(parts)

    # johndoe@… → try splitting
    if 6 <= len(local) <= 20 and local.isalpha():
        for i in range(3, min(8, len(local))):
            first, second = local[:i], local[i:]
            if first.isalpha() and second.isalpha():
                return f"{first.capitalize()} {second.capitalize()}"

    return None


# ── Public API ──────────────────────────────────────────────────────────────

def extract_name_from_text(text: str) -> Optional[str]:
    """Extract candidate name from resume text using multiple heuristics."""
    if not text or len(text.strip()) < 10:
        return None

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # ── Strategy 1: First non-header line that looks like a name ────────────
    for idx in range(min(2, len(lines))):
        line = lines[idx]
        if _line_is_header(line):
            continue
        name = _extract_name_words(line)
        if name:
            return name

    # ── Strategy 2: Explicit "Name:" patterns ───────────────────────────────
    name_patterns = [
        r'(?:Name|Full Name|Candidate Name|Applicant)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'^([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\n|$)',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Email|Phone|Resume)',
    ]
    for pattern in name_patterns:
        for match in re.findall(pattern, text, re.MULTILINE | re.IGNORECASE):
            candidate = match.strip()
            if len(candidate.split()) >= 2 and len(candidate) < 50:
                if not any(p in candidate.lower() for p in NON_NAME_PHRASES):
                    return candidate

    # ── Strategy 3: Derive name from email address ──────────────────────────
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
    for email in emails:
        name = _name_from_email(email)
        if name:
            return name

    # ── Strategy 4: Capitalized 2-4 word lines in first 8 lines ─────────────
    for line in lines[:8]:
        if any(sw in line.lower() for sw in SKIP_LINE_WORDS):
            continue
        words = line.split()
        if 2 <= len(words) <= 4:
            caps = []
            for w in words:
                cleaned = re.sub(r'[^\w\s-]', '', w)
                if cleaned and cleaned[0].isupper() and sum(c.isalpha() for c in cleaned) > len(cleaned) * 0.8:
                    caps.append(cleaned)
            if len(caps) >= 2:
                return ' '.join(caps)

    return None


def extract_contact_info(text: str) -> dict[str, str | None]:
    """
    Extract contact details (email, phone, GitHub) from resume text.

    Returns a dict with keys 'email', 'phone', 'github' — each may be None.
    """
    info: dict[str, str | None] = {"email": None, "phone": None, "github": None}

    if not text:
        return info

    # Email – first match
    email_match = re.search(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text,
    )
    if email_match:
        info["email"] = email_match.group(0).lower()

    # Phone – supports +1 (555) 123-4567, 555-123-4567, 555.123.4567, etc.
    phone_match = re.search(
        r'(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}\b',
        text,
    )
    if phone_match:
        raw = phone_match.group(0).strip()
        digits = re.sub(r'\D', '', raw)
        if 7 <= len(digits) <= 15:          # reject unlikely lengths
            info["phone"] = raw

    # GitHub – github.com/username or github.com/username/
    gh_match = re.search(
        r'(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_-]+)',
        text, re.IGNORECASE,
    )
    if gh_match:
        info["github"] = f"https://github.com/{gh_match.group(1)}"

    return info


def extract_text(file_path: str) -> str:
    """Extract plain text from a PDF or DOCX file."""
    lower = file_path.lower()

    if lower.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    if lower.endswith(".docx"):
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    return ""
