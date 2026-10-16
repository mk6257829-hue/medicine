"""
run.py — Application entry point.

Usage:
    python run.py
"""

import os
from dotenv import load_dotenv

load_dotenv()  # load .env before creating the app

from app import create_app

env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = app.config.get("DEBUG", True)
    app.run(host="0.0.0.0", port=port, debug=debug)
