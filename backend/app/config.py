import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
STORAGE_DIR = DATA_DIR / "storage"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'fintech.db'}"

# Ingestion configuration
DEFAULT_HISTORY_YEARS = 5
SEC_EDGAR_USER_AGENT = "FintechIntelligencePlatform/1.0 (compliance@fintechplatform.enterprise)"

# FR-004: Automated report monitoring interval (minutes)
AUTO_UPDATE_POLL_INTERVAL_MINUTES = 60
