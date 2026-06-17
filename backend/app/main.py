"""Точка входа FastAPI: API + статический фронтенд SPA."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .routers import activities, admin, athletes, public, routes, watch

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="SwimBuoy", version="0.1.0",
              description="Маршруты буёв, треки заплывов и отчёты для открытой воды.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    if settings.demo_bootstrap:
        from .db import SessionLocal
        from .services.demo import bootstrap_demo
        db = SessionLocal()
        try:
            bootstrap_demo(db)
        except Exception:
            db.rollback()
        finally:
            db.close()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "base_url": settings.base_url}


app.include_router(athletes.router)
app.include_router(admin.router)
app.include_router(routes.router)
app.include_router(activities.router)
app.include_router(watch.router)
app.include_router(public.router)


# --- Статический фронтенд (SPA) ---
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    # SPA-фолбэк: любые не-API пути отдают index.html (роутинг через hash).
    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
