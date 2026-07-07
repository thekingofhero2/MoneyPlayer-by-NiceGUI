import threading
import time
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

# 视频任务调度器线程
_scheduler_thread = None
_scheduler_lock = threading.Lock()


def _start_scheduler():
    """启动视频任务调度器线程"""
    global _scheduler_thread
    with _scheduler_lock:
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            from src.app_videomaker import make_video
            _scheduler_thread = threading.Thread(target=make_video.main, daemon=True)
            _scheduler_thread.start()
            print("INFO:     Video task scheduler started.")
            return True
    return False


def _monitor_scheduler():
    """监控调度器线程状态，如果挂了就重启"""
    global _scheduler_thread
    while True:
        time.sleep(30)  # 每30秒检查一次
        with _scheduler_lock:
            if _scheduler_thread is None or not _scheduler_thread.is_alive():
                print("WARNING:  Video scheduler thread died, restarting...")
                from src.app_videomaker import make_video
                _scheduler_thread = threading.Thread(target=make_video.main, daemon=True)
                _scheduler_thread.start()
                print("INFO:     Video task scheduler restarted.")


async def on_startup():
    """Initializes the database on application startup."""
    print("INFO:     Initializing database...")
    init_db.init()
    print("INFO:     Database initialization complete.")

    # 启动视频任务调度器
    _start_scheduler()

    # 启动调度器监控线程
    monitor_thread = threading.Thread(target=_monitor_scheduler, daemon=True)
    monitor_thread.start()
    print("INFO:     Scheduler monitor started.")


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
        title="MoneyPrinter-by-NiceGUI",
        port=8000,
        storage_secret=settings.SECRET_KEY,
        reload=True,
        fastapi_docs=True,
    )
