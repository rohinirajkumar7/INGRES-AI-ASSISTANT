"""Vercel entrypoint: exposes the ASGI `app` that Vercel's Python runtime serves."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingres.app import app  # noqa: E402,F401
