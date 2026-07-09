from nicegui import ui, app


@ui.page("/video-player")
async def video_player_page():
    """视频播放页面"""
    with ui.header().classes("bg-primary text-white"):
        with ui.row().classes("items-center w-full"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/video-production")).props("flat round color=white")
            ui.label("视频预览").classes("text-lg font-bold")

    video_path = None
    try:
        video_path = app.storage.user.get("video_path", None)
    except:
        pass

    if not video_path:
        with ui.column().classes("items-center justify-center w-full").style("height: 80vh"):
            ui.label("未找到视频文件").classes("text-xl text-gray-500")
            ui.button("返回", on_click=lambda: ui.navigate.to("/video-production")).classes("mt-4")
        return

    with ui.column().classes("items-center w-full").style("height: calc(100vh - 60px)"):
        ui.video(
            video_path,
            autoplay=True,
            controls=True,
        ).classes("max-w-5xl").style("max-height: 80vh; width: 100%")
