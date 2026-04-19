"""Vercel backend service entrypoint.

This shim keeps imports package-based by exposing the FastAPI app from backend.main.
"""

from backend.main import app
