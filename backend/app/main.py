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
    description="Enterprise Financial Intelligence Engine implementing FR-001 to FR-004 (Data Management), FR-005 to FR-009 (Market Intelligence), FR-010 to FR-014 (Knowledge & RAG), FR-015 to FR-023 (Multi-Agent System), FR-028 to FR-033 (Predictive Analytics), FR-034 to FR-036 (Scenario Analysis), and FR-037 to FR-040 (Strategic Recommendations).",
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

# Mount Frontend static files (Prioritize React Claymorphic SPA Build)
REACT_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend-react" / "dist"
VANILLA_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if REACT_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(REACT_DIST_DIR), html=True), name="frontend-react")
elif VANILLA_FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(VANILLA_FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
