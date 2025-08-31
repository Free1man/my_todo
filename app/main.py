"""Expose the new tactical backend under app.main:app to keep Docker wiring intact."""
from backend.app import app  # re-export FastAPI app
