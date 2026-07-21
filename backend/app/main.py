"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.routers import videos, imports, exports, coding, audit, search_sessions, mediacrawler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    # Ensure media storage directory exists
    Path(settings.MEDIA_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent.parent.parent / "frontend" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# API Routers
app.include_router(videos.router)
app.include_router(imports.router)
app.include_router(exports.router)
app.include_router(coding.router)
app.include_router(audit.router)
app.include_router(search_sessions.router)
app.include_router(mediacrawler.router)


# ── Frontend pages (server-side Jinja2 + HTMX) ──

@app.get("/")
async def index(request: Request):
    """Dashboard — main entry page."""
    return templates.TemplateResponse("pages/dashboard.html", {"request": request})


@app.get("/videos")
async def videos_page(request: Request):
    """Video list page."""
    return templates.TemplateResponse("pages/videos.html", {"request": request})


@app.get("/videos/{video_id}")
async def video_detail_page(request: Request, video_id: str):
    """Video detail and editing page."""
    return templates.TemplateResponse(
        "pages/video_detail.html",
        {"request": request, "video_id": video_id},
    )


@app.get("/import")
async def import_page(request: Request):
    """Import page — link paste, CSV/XLSX upload, browser extract."""
    return templates.TemplateResponse("pages/import.html", {"request": request})


@app.get("/export")
async def export_page(request: Request):
    """Export page."""
    return templates.TemplateResponse("pages/export.html", {"request": request})


@app.get("/coding")
async def coding_page(request: Request):
    """Coding page."""
    return templates.TemplateResponse("pages/coding.html", {"request": request})


@app.get("/quality")
async def quality_page(request: Request):
    """Data quality report page."""
    return templates.TemplateResponse("pages/quality.html", {"request": request})


@app.get("/audit")
async def audit_page(request: Request):
    """Audit log page."""
    return templates.TemplateResponse("pages/audit.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.VERSION}
