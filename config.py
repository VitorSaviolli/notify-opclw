import os
from zoneinfo import ZoneInfo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# OpenClaw
OPENCLAW_API_URL = os.getenv("OPENCLAW_API_URL", "http://localhost:3000/api/v1/chat")
OPENCLAW_API_KEY = os.getenv("OPENCLAW_API_KEY", "")
OPENCLAW_WEBHOOK_SECRET = os.getenv("OPENCLAW_WEBHOOK_SECRET", "")

# Bot
BOT_PORT = int(os.getenv("BOT_PORT", "5000"))
TZ = ZoneInfo("America/Sao_Paulo")

# Defaults
DEFAULT_ANTECEDENCIA_MIN = 10
INSISTENCE_INTERVAL_MIN = 5
INSISTENCE_MAX = 10
HISTORY_LIMIT = 20

# Database (persiste em /app/data no Docker)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "notificador.db")


def now():
    return datetime.now(TZ)
