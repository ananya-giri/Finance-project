import sys
from pathlib import Path
from contextlib import asynccontextmanager

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.database import init_db
from backend.app.services.scheduler_service import SchedulerService
from backend.app.api.router import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Start FR-004 Scheduler
    init_db()
    SchedulerService.start()
    yield
    # Shutdown
    SchedulerService.stop()

app = FastAPI(
    title="Agentic AI Financial Intelligence & Data Management Platform",
    description="Enterprise Financial Intelligence Engine implementing FR-001 (5-Year Historical Ingestion), FR-002 (Multi-Type Document Ingestion), FR-003 (Structured Financial Metrics), and FR-004 (Automated Report Watcher).",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(router)

# Mount Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
