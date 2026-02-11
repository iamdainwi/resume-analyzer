"""
Vercel serverless entry point.

This thin wrapper re-exports the FastAPI app so that Vercel's
@vercel/python runtime can discover it. The actual application
logic lives in app/main.py.
"""

from app.main import app  # noqa: F401 — Vercel looks for `app`
