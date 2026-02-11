"""
Centralized configuration — all settings loaded from environment variables
with sensible defaults for local development.

On Vercel (serverless), the filesystem is read-only except /tmp.
We detect the VERCEL environment variable and adjust paths automatically.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Runtime detection ───────────────────────────────────────────────────────
IS_VERCEL: bool = bool(os.getenv("VERCEL"))

# ── Database ────────────────────────────────────────────────────────────────
_default_db = "sqlite:////tmp/hr.db" if IS_VERCEL else "sqlite:///./hr.db"
DATABASE_URL: str = os.getenv("DATABASE_URL", _default_db)

# ── Ollama / LLM ───────────────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")

# ── CORS ────────────────────────────────────────────────────────────────────
# Comma-separated origins, e.g. "http://localhost:3000,https://app.example.com"
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ── File Uploads ────────────────────────────────────────────────────────────
_default_upload = "/tmp/uploads" if IS_VERCEL else "uploads"
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", _default_upload)
MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "20"))
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".doc"}

# ── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── LLM Limits ──────────────────────────────────────────────────────────────
MAX_JD_CHARS: int = int(os.getenv("MAX_JD_CHARS", "1500"))
MAX_RESUME_CHARS: int = int(os.getenv("MAX_RESUME_CHARS", "3000"))
