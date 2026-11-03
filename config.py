"""Runtime settings; environment variables override local defaults."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'tableflow.db'}")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
RESTAURANT_NAME = os.getenv("RESTAURANT_NAME", "Restaurant Demo")
