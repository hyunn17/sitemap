import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
DB_PATH = Path(os.getenv("DB_PATH", str(ROOT / "data" / "shorts.db")))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
AUTO_COLLECT_HOURS = float(os.getenv("AUTO_COLLECT_HOURS", "0") or 0)
AUTO_COLLECT_KEYWORDS = [
    k.strip() for k in os.getenv("AUTO_COLLECT_KEYWORDS", "").split(",") if k.strip()
]
USER_AGENT = "shorts-script-app/0.1 (personal research tool)"
