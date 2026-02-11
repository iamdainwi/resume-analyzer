"""
Vercel serverless entry point.

This thin wrapper re-exports the FastAPI app so that Vercel's
@vercel/python runtime can discover it.
"""
import os
import sys

# Add the parent directory to sys.path so 'main' and 'app' can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    # Since main.py is in the root backend/ directory now
    from main import app
except ImportError as e:
    # If import fails, we'll try to log it or raise a clear error
    # Vercel's logs should capture this
    print(f"Failed to import app: {e}")
    raise
