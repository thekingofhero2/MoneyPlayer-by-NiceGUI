from nicegui import app, ui
from fastapi.middleware.cors import CORSMiddleware

from src.backend.endpoints import login, users, items, video_scripts
from src.core.config import settings
from src.db import init_db

# ruff: noqa: F401
from src.frontend.pages import (
    home,
    create_user,
    items as items_page,
    login as login_page,
    register as register_page,
    profile as profile_page,
    video_scripts as video_scripts_page,
    video_production as video_production_page,
)


async def on_startup():
    """Initializes the database on application startup."""
    print("INFO:     Initializing database...")
    init_db.init()
    print("INFO:     Database initialization complete.")


async def on_shutdown():
    """Actions to perform on application shutdown."""
    print("INFO:     Application shutting down.")


app.on_startup(on_startup)
app.on_shutdown(on_shutdown)

# Add CORS middleware
#   - Only for external apps.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You should restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(login.router, tags=["login"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(video_scripts.router, prefix="/api/v1", tags=["video-scripts"])

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="NiceGUI FastAPI Template",
        port=8000,
        storage_secret=settings.SECRET_KEY,
        reload=True,
        fastapi_docs=True,
    )
