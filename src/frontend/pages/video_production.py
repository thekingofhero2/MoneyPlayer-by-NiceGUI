import asyncio
import json
from nicegui import ui, app
from src.frontend.layouts.default import dashboard_frame
from src.frontend.components import notifications
from src.frontend.components.auth_utils import get_current_user_from_state
from src.db.session import get_db_context
from src.repositories.video_task import video_task_repo, user_video_config_repo
from src.repositories.video_script import video_script_repo
from src.models import VideoTaskCreate, UserVideoConfigCreate


@ui.page("/video-production")
def video_production_page():
    """视频制作页面"""
    with dashboard_frame(title="视频制作"):
        # 获取当前用户
        with get_db_context() as db:
            try:
                current_user = get_current_user_from_state(db)
            except Exception:
                ui.navigate.to("/login")
                return

        # 页面标题
        ui.label("视频制作配置").classes("text-2xl font-bold mb-6")

        # 创建选项卡
        with ui.tabs().classes('w-full') as tabs:
            config_tab = ui.tab('全局配置')
            task_config_tab = ui.tab('任务配置')
            task_list_tab = ui.tab('任务清单')

        with ui.tab_panels(tabs, value=task_config_tab).classes('w-full mt-4'):
            # 选项卡 1: 全局配置
            with ui.tab_panel(config_tab):
                render_global_config_section()

            # 选项卡 2: 任务配置
            with ui.tab_panel(task_config_tab):
                render_task_config_section()

            # 选项卡 3: 任务清单
            with ui.tab_panel(task_list_tab):
                render_task_list_section()


def render_global_config_section():
    """渲染全局配置区域"""
    with ui.card().classes('w-full p-6'):
        ui.label("全局配置").classes("text-xl font-bold mb-4")
        ui.label("这些配置将作为默认值用于新任务").classes("text-gray-600 mb-6")
        
        # 视频来源配置
        ui.label("视频来源配置").classes("text-lg font-bold mb-3")
        with ui.row().classes("w-full items-center gap-4 mb-4"):
            ui.label("默认视频来源：").classes("font-bold")
            source_type = ui.radio(
                {"pexels": "Pexels 在线素材", "local": "本地视频目录"},
                value="pexels",
            ).classes("flex-1")
        
        # Pexels API Key 配置
        with ui.card().classes("w-full p-4 mb-4").bind_visibility_from(source_type, "value", lambda v: v == "pexels") as pexels_card:
            ui.label("Pexels API Key").classes("text-lg font-bold mb-2")
            pexels_api_key = ui.input(
                "API Key",
                placeholder="获取地址：https://www.pexels.com/api/",
                password=True
            ).classes("w-full")
            ui.markdown("💡 [点击申请 Pexels API Key](https://www.pexels.com/api/)").classes("text-sm text-gray-600")
        
        # 本地视频目录配置
        with ui.card().classes("w-full p-4 mb-4").bind_visibility_from(source_type, "value", lambda v: v == "local") as local_card:
            ui.label("本地视频目录").classes("text-lg font-bold mb-2")
            with ui.row().classes("w-full gap-2"):
                local_video_dir = ui.input(
                    "目录路径",
                    placeholder="例如：D:/Videos"
                ).classes("flex-1")
                ui.button("浏览", icon="folder_open", on_click=lambda: local_video_dir.run_method("(e) => e.target.showPicker()")).props("flat")
            
            # 目录验证提示
            dir_status = ui.label().classes("text-sm mt-2")
            
            def validate_dir():
                import os
                if local_video_dir.value and os.path.isdir(local_video_dir.value):
                    dir_status.set_text(f"✓ 目录有效：{local_video_dir.value}")
                    dir_status.classes("text-green-600")
                elif local_video_dir.value:
                    dir_status.set_text(f"✗ 目录不存在：{local_video_dir.value}")
                    dir_status.classes("text-red-600")
                else:
                    dir_status.set_text("")
            
            local_video_dir.on("blur", validate_dir)
        
        ui.separator().classes("my-6")
        
        # TTS 语音服务器配置
        ui.label("TTS 语音服务器配置").classes("text-lg font-bold mb-3")
        
        with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
            # 硅基流动
            with ui.card().classes("p-4"):
                ui.label("硅基流动 API Key").classes("font-bold mb-2")
                siliflow_api_key = ui.input(
                    "API Key",
                    placeholder="sk-...",
                    password=True
                ).classes("w-full")
            
            # 小米 Mimo
            with ui.card().classes("p-4"):
                ui.label("小米 Mimo API Key").classes("font-bold mb-2")
                mimo_api_key = ui.input(
                    "API Key",
                    placeholder="请输入 API Key",
                    password=True
                ).classes("w-full")
            
            # Azure 语音
            with ui.card().classes("p-4"):
                ui.label("Azure 语音 API Key").classes("font-bold mb-2")
                azure_api_key = ui.input(
                    "API Key",
                    placeholder="请输入 Azure API Key",
                    password=True
                ).classes("w-full")
        
        ui.separator().classes("my-6")
        
        # # 默认视频参数
        # ui.label("默认视频参数").classes("text-lg font-bold mb-3")
        
        # with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
        #     # 视频比例
        #     with ui.column().classes("col-span-1"):
        #         ui.label("默认视频比例").classes("text-sm font-bold mb-1")
        #         default_video_aspect = ui.select(
        #             {"16:9": "16:9 (横屏)", "9:16": "9:16 (竖屏)"},
        #             value="9:16",
        #         ).classes("w-full")
            
        #     # 拼接模式
        #     with ui.column().classes("col-span-1"):
        #         ui.label("默认拼接模式").classes("text-sm font-bold mb-1")
        #         default_concat_mode = ui.select(
        #             {"sequential": "顺序拼接", "random": "随机拼接"},
        #             value="random",
        #         ).classes("w-full")
            
        #     # 片段时长
        #     with ui.column().classes("col-span-1"):
        #         ui.label("默认片段时长（秒）").classes("text-sm font-bold mb-1")
        #         default_clip_duration = ui.slider(min=1, max=20, step=1, value=5).props("label-always snap").classes("w-full")
            
        #     # 线程数
        #     with ui.column().classes("col-span-1"):
        #         ui.label("线程数").classes("text-sm font-bold mb-1")
        #         default_n_threads = ui.slider(min=1, max=8, step=1, value=2).props("label-always snap").classes("w-full")
        
        # ui.separator().classes("my-6")
        
        # # 默认音频参数
        # ui.label("默认音频参数").classes("text-lg font-bold mb-3")
        
        # with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
        #     # 语音名称
        #     with ui.column().classes("col-span-1"):
        #         ui.label("默认语音名称").classes("text-sm font-bold mb-1")
        #         default_voice_name = ui.select(
        #             {
        #                 "zh-CN-XiaoxiaoNeural-Female": "晓晓（女声）",
        #                 "zh-CN-YunxiNeural-Male": "云希（男声）",
        #                 "zh-CN-YunyangNeural-Male": "云扬（男声）",
        #                 "zh-CN-XiaoyiNeural-Female": "晓伊（女声）",
        #                 "zh-CN-YunjianNeural-Male": "云健（男声）",
        #             },
        #             value="zh-CN-XiaoxiaoNeural-Female",
        #         ).classes("w-full")
            
        #     # 语音音量
        #     with ui.column().classes("col-span-1"):
        #         ui.label("默认语音音量").classes("text-sm font-bold mb-1")
        #         default_voice_volume = ui.slider(min=0, max=2, step=0.1, value=1.0).props("label-always").classes("w-full")
            
        #     # 语音速度
        #     with ui.column().classes("col-span-1"):
        #         ui.label("默认语音速度").classes("text-sm font-bold mb-1")
        #         default_voice_rate = ui.slider(min=0.5, max=2, step=0.1, value=1.0).props("label-always").classes("w-full")
            
        #     # 背景音乐类型
        #     with ui.column().classes("col-span-1"):
        #         ui.label("背景音乐类型").classes("text-sm font-bold mb-1")
        #         default_bgm_type = ui.select(
        #             {"random": "随机", "custom": "自定义"},
        #             value="random",
        #         ).classes("w-full")
            
        #     # 背景音乐文件
        #     with ui.column().classes("col-span-1"):
        #         ui.label("背景音乐文件").classes("text-sm font-bold mb-1")
        #         default_bgm_file = ui.input("文件路径", placeholder="留空使用随机").classes("w-full")
            
        #     # 背景音乐音量
        #     with ui.column().classes("col-span-1"):
        #         ui.label("背景音乐音量").classes("text-sm font-bold mb-1")
        #         default_bgm_volume = ui.slider(min=0, max=1, step=0.05, value=0.2).props("label-always").classes("w-full")
        
        # ui.separator().classes("my-6")
        
        # # 默认字幕参数
        # ui.label("默认字幕参数").classes("text-lg font-bold mb-3")
        
        # with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
        #     # 是否启用字幕
        #     with ui.column().classes("col-span-1"):
        #         ui.label("启用字幕").classes("text-sm font-bold mb-1")
        #         default_subtitle_enabled = ui.switch(value=True).classes("w-full")
            
        #     # 字幕位置
        #     with ui.column().classes("col-span-1"):
        #         ui.label("字幕位置").classes("text-sm font-bold mb-1")
        #         default_subtitle_position = ui.select(
        #             {"top": "顶部", "middle": "中间", "bottom": "底部"},
        #             value="bottom",
        #         ).classes("w-full")
            
        #     # 自定义位置
        #     with ui.column().classes("col-span-1"):
        #         ui.label("自定义位置（%）").classes("text-sm font-bold mb-1")
        #         default_custom_position = ui.slider(min=0, max=100, step=1, value=70).props("label-always snap").classes("w-full")
            
        #     # 字体名称
        #     with ui.column().classes("col-span-1"):
        #         ui.label("字体名称").classes("text-sm font-bold mb-1")
        #         default_font_name = ui.select(
        #             {
        #                 "STHeitiMedium.ttc": "黑体",
        #                 "STSong.ttc": "宋体",
        #                 "Arial": "Arial",
        #                 "Microsoft YaHei": "微软雅黑",
        #             },
        #             value="STHeitiMedium.ttc",
        #         ).classes("w-full")
            
        #     # 字体大小
        #     with ui.column().classes("col-span-1"):
        #         ui.label("字体大小").classes("text-sm font-bold mb-1")
        #         default_font_size = ui.slider(min=20, max=100, step=2, value=60).props("label-always snap").classes("w-full")
            
        #     # 字体颜色
        #     with ui.column().classes("col-span-1"):
        #         ui.label("字体颜色").classes("text-sm font-bold mb-1")
        #         default_text_fore_color = ui.color_input("", value="#FFFFFF").classes("w-full")
            
        #     # 描边颜色
        #     with ui.column().classes("col-span-1"):
        #         ui.label("描边颜色").classes("text-sm font-bold mb-1")
        #         default_stroke_color = ui.color_input("", value="#000000").classes("w-full")
            
        #     # 描边宽度
        #     with ui.column().classes("col-span-1"):
        #         ui.label("描边宽度").classes("text-sm font-bold mb-1")
        #         default_stroke_width = ui.slider(min=0, max=5, step=0.5, value=1.5).props("label-always snap").classes("w-full")
            
        #     # 启用字幕背景
        #     with ui.column().classes("col-span-1"):
        #         ui.label("启用字幕背景").classes("text-sm font-bold mb-1")
        #         default_text_background_color = ui.switch(value=True).classes("w-full")
            
        #     # 圆角字幕背景
        #     with ui.column().classes("col-span-1"):
        #         ui.label("圆角字幕背景").classes("text-sm font-bold mb-1")
        #         default_rounded_subtitle_background = ui.switch(value=False).classes("w-full")
        
        # 保存按钮
        with ui.row().classes("w-full justify-end mt-6 gap-2"):
            async def save_global_config():
                """保存全局配置到数据库"""
                # 验证视频来源配置
                if source_type.value == "pexels" and not pexels_api_key.value:
                    notifications.show_error("使用 Pexels 时需要配置 API Key")
                    return
                if source_type.value == "local" and not local_video_dir.value:
                    notifications.show_error("使用本地视频时需要指定目录路径")
                    return
                
                try:
                    with get_db_context() as db:
                        current_user = get_current_user_from_state(db)
                        
                        config_in = UserVideoConfigCreate(
                            pexels_api_key=pexels_api_key.value if source_type.value == "pexels" else None,
                            local_video_dir=local_video_dir.value if source_type.value == "local" else None,
                            siliflow_api_key=siliflow_api_key.value,
                            mimo_api_key=mimo_api_key.value,
                            azure_api_key=azure_api_key.value,
                            # default_volume=default_voice_volume.value,
                            # default_speed=default_voice_rate.value,
                            # default_bgm=default_bgm_file.value,
                            # default_bgm_volume=default_bgm_volume.value,
                            # default_font=default_font_name.value,
                            # default_font_position=default_subtitle_position.value,
                            # default_font_color=default_text_fore_color.value,
                            # default_bg_color=default_stroke_color.value,
                            # default_enable_bg=default_text_background_color.value,
                        )
                        
                        config = user_video_config_repo.create_or_update(
                            db=db, obj_in=config_in, current_user_id=current_user.id
                        )
                    
                    notifications.show_success("全局配置已保存到数据库！")
                except Exception as e:
                    notifications.show_error(f"保存失败：{str(e)}")
            
            ui.button("保存配置", icon="save", on_click=save_global_config).props("color=primary size=lg")
        
        # 加载用户配置
        async def load_user_config():
            """从数据库加载用户配置"""
            try:
                with get_db_context() as db:
                    current_user = get_current_user_from_state(db)
                    config = user_video_config_repo.get_for_user(
                        db=db, current_user_id=current_user.id
                    )
                    
                    if config:
                        # 视频来源配置
                        if config.pexels_api_key:
                            source_type.value = "pexels"
                            pexels_api_key.value = config.pexels_api_key
                        if config.local_video_dir:
                            source_type.value = "local"
                            local_video_dir.value = config.local_video_dir
                        
                        # TTS 配置
                        siliflow_api_key.value = config.siliflow_api_key or ""
                        mimo_api_key.value = config.mimo_api_key or ""
                        azure_api_key.value = config.azure_api_key or ""
                        
                        # 默认设置
                        default_voice_volume.value = config.default_volume
                        default_voice_rate.value = config.default_speed
                        default_bgm_file.value = config.default_bgm or ""
                        default_bgm_volume.value = config.default_bgm_volume
                        default_font_name.value = config.default_font
                        default_subtitle_position.value = config.default_font_position
                        default_text_fore_color.value = config.default_font_color
                        default_stroke_color.value = config.default_bg_color
                        default_text_background_color.value = config.default_enable_bg
            except Exception as e:
                pass
        
        # 页面加载时自动加载配置
        ui.timer(0.1, lambda: load_user_config(), once=True)


def render_task_config_section():
    """渲染任务配置区域"""
    with ui.card().classes('w-full p-6'):
        ui.label("创建新任务").classes("text-xl font-bold mb-4")
        
        # 1. 视频主题
        ui.label("1. 视频主题").classes("text-lg font-bold mb-2")
        video_subject = ui.input(
            "视频主题",
            placeholder="例如：春天的花海",
        ).classes("w-full mb-4")
        
        # 2. 选择文案
        ui.label("2. 选择文案").classes("text-lg font-bold mb-2")
        script_options = {}
        selected_script_content = {"value": None, "search_terms": None}
        
        async def load_scripts():
            """加载用户文案列表"""
            try:
                with get_db_context() as db:
                    current_user = get_current_user_from_state(db)
                    scripts = video_script_repo.get_for_user(db=db, current_user_id=current_user.id)
                    
                    # 按时间倒序
                    scripts = sorted(scripts, key=lambda x: x.created_at or "", reverse=True)
                    
                    # 构建选项
                    script_options.clear()
                    for script in scripts:
                        preview = script.content[:50].replace("\n", " ") + "..." if len(script.content) > 50 else script.content
                        script_options[script.id] = f"{script.theme} - {preview}"
                    
                    # 更新选项
                    script_select.options = script_options
                    if script_options:
                        script_select.value = list(script_options.keys())[0]
            except Exception as e:
                pass
        
        
        def on_script_change():
            """当选择文案时，更新内容"""
            if script_select.value:
                try:
                    with get_db_context() as db:
                        current_user = get_current_user_from_state(db)
                        script = video_script_repo.get_by_id(db=db, script_id=script_select.value)
                        if script and script.user_id == current_user.id:
                            video_subject.value = script.theme
                            selected_script_content["value"] = script.content
                            selected_script_content["search_terms"] = script.keywords
                except Exception as e:
                    import traceback
                    traceback.print_exc()
        script_select = ui.select(
            {},
            label="选择已生成的文案",
            value=None,
            on_change=lambda e: on_script_change()
        ).classes("w-full mb-4")
        
        #script_select.on("update:model-value", on_script_change)
        
        # 刷新文案列表按钮
        ui.button("刷新文案列表", icon="refresh", on_click=load_scripts).props("flat size=sm mb-4")
        
        # 加载文案列表
        load_scripts()
        
        ui.separator().classes("my-4")
        
        # 3. 视频参数
        ui.label("3. 视频参数").classes("text-lg font-bold mb-3")
        
        with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
            # 视频来源
            with ui.column().classes("col-span-1"):
                ui.label("视频来源").classes("text-sm font-bold mb-1")
                video_source = ui.radio(
                    {"pexels": "Pexels 在线素材", "local": "本地视频目录"},
                    value="pexels",
                ).classes("w-full")
            
            # 视频比例
            with ui.column().classes("col-span-1"):
                ui.label("视频比例").classes("text-sm font-bold mb-1")
                video_aspect = ui.select(
                    {"16:9": "16:9 (横屏)", "9:16": "9:16 (竖屏)"},
                    value="9:16",
                ).classes("w-full")
            
            # 拼接模式
            with ui.column().classes("col-span-1"):
                ui.label("拼接模式").classes("text-sm font-bold mb-1")
                video_concat_mode = ui.select(
                    {"sequential": "顺序拼接", "random": "随机拼接"},
                    value="random",
                ).classes("w-full")
            
            # 片段时长
            with ui.column().classes("col-span-1"):
                ui.label("片段时长（秒）").classes("text-sm font-bold mb-1")
                video_clip_duration = ui.slider(min=1, max=20, step=1, value=5).props("label-always snap").classes("w-full")
            
            # 视频数量
            with ui.column().classes("col-span-1"):
                ui.label("视频数量").classes("text-sm font-bold mb-1")
                video_count = ui.slider(min=1, max=10, step=1, value=1).props("label-always snap").classes("w-full")
            
            # 线程数
            with ui.column().classes("col-span-1"):
                ui.label("线程数").classes("text-sm font-bold mb-1")
                n_threads = ui.slider(min=1, max=8, step=1, value=2).props("label-always snap").classes("w-full")
        
        ui.separator().classes("my-4")
        
        # 4. 音频参数
        ui.label("4. 音频参数").classes("text-lg font-bold mb-3")
        
        with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
            # 语音名称
            with ui.column().classes("col-span-1"):
                ui.label("语音名称").classes("text-sm font-bold mb-1")
                voice_name = ui.select(
                    {
                        "zh-CN-XiaoxiaoNeural-Female": "晓晓（女声）",
                        "zh-CN-YunxiNeural-Male": "云希（男声）",
                        "zh-CN-YunyangNeural-Male": "云扬（男声）",
                        "zh-CN-XiaoyiNeural-Female": "晓伊（女声）",
                        "zh-CN-YunjianNeural-Male": "云健（男声）",
                    },
                    value="zh-CN-XiaoxiaoNeural-Female",
                ).classes("w-full")
            
            # 语音音量
            with ui.column().classes("col-span-1"):
                ui.label("语音音量").classes("text-sm font-bold mb-1")
                voice_volume = ui.slider(min=0, max=2, step=0.1, value=1.0).props("label-always").classes("w-full")
            
            # 语音速度
            with ui.column().classes("col-span-1"):
                ui.label("语音速度").classes("text-sm font-bold mb-1")
                voice_rate = ui.slider(min=0.5, max=2, step=0.1, value=1.0).props("label-always").classes("w-full")
            
            # 背景音乐类型
            with ui.column().classes("col-span-1"):
                ui.label("背景音乐类型").classes("text-sm font-bold mb-1")
                bgm_type = ui.select(
                    {"random": "随机", "custom": "自定义"},
                    value="random",
                ).classes("w-full")
            
            # 背景音乐文件
            with ui.column().classes("col-span-1"):
                ui.label("背景音乐文件").classes("text-sm font-bold mb-1")
                bgm_file = ui.input("文件路径", placeholder="留空使用随机").classes("w-full")
            
            # 背景音乐音量
            with ui.column().classes("col-span-1"):
                ui.label("背景音乐音量").classes("text-sm font-bold mb-1")
                bgm_volume = ui.slider(min=0, max=1, step=0.05, value=0.2).props("label-always").classes("w-full")
        
        ui.separator().classes("my-4")
        
        # 5. 字幕参数
        ui.label("5. 字幕参数").classes("text-lg font-bold mb-3")
        
        with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4 mb-4"):
            # 是否启用字幕
            with ui.column().classes("col-span-1"):
                ui.label("启用字幕").classes("text-sm font-bold mb-1")
                subtitle_enabled = ui.switch(value=True).classes("w-full")
            
            # 字幕位置
            with ui.column().classes("col-span-1"):
                ui.label("字幕位置").classes("text-sm font-bold mb-1")
                subtitle_position = ui.select(
                    {"top": "顶部", "middle": "中间", "bottom": "底部"},
                    value="bottom",
                ).classes("w-full")
            
            # 自定义位置
            with ui.column().classes("col-span-1"):
                ui.label("自定义位置（%）").classes("text-sm font-bold mb-1")
                custom_position = ui.slider(min=0, max=100, step=1, value=70).props("label-always snap").classes("w-full")
            
            # 字体名称
            with ui.column().classes("col-span-1"):
                ui.label("字体名称").classes("text-sm font-bold mb-1")
                font_name = ui.select(
                    {
                        "STHeitiMedium.ttc": "黑体",
                        "STSong.ttc": "宋体",
                        "Arial": "Arial",
                        "Microsoft YaHei": "微软雅黑",
                    },
                    value="STHeitiMedium.ttc",
                ).classes("w-full")
            
            # 字体大小
            with ui.column().classes("col-span-1"):
                ui.label("字体大小").classes("text-sm font-bold mb-1")
                font_size = ui.slider(min=20, max=100, step=2, value=60).props("label-always snap").classes("w-full")
            
            # 字体颜色
            with ui.column().classes("col-span-1"):
                ui.label("字体颜色").classes("text-sm font-bold mb-1")
                text_fore_color = ui.color_input("", value="#FFFFFF").classes("w-full")
            
            # 描边颜色
            with ui.column().classes("col-span-1"):
                ui.label("描边颜色").classes("text-sm font-bold mb-1")
                stroke_color = ui.color_input("", value="#000000").classes("w-full")
            
            # 描边宽度
            with ui.column().classes("col-span-1"):
                ui.label("描边宽度").classes("text-sm font-bold mb-1")
                stroke_width = ui.slider(min=0, max=5, step=0.5, value=1.5).props("label-always snap").classes("w-full")
            
            # 启用字幕背景
            with ui.column().classes("col-span-1"):
                ui.label("启用字幕背景").classes("text-sm font-bold mb-1")
                text_background_color = ui.switch(value=True).classes("w-full")
            
            # 圆角字幕背景
            with ui.column().classes("col-span-1"):
                ui.label("圆角字幕背景").classes("text-sm font-bold mb-1")
                rounded_subtitle_background = ui.switch(value=False).classes("w-full")
        
        ui.separator().classes("my-4")
        
        # 创建任务按钮
        with ui.row().classes("w-full justify-end mt-4 gap-2"):
            async def create_task():
                """创建视频任务"""
                # 验证
                if not script_select.value:
                    notifications.show_error("请选择文案")
                    return
                if not video_subject.value:
                    notifications.show_error("请输入视频主题")
                    return
                
                if not selected_script_content["value"]:
                    notifications.show_error("请重新选择文案")
                    return
                
                # 构建完整的 script.json 格式
                script_json = {
                    "script": selected_script_content["value"],
                    "search_terms": selected_script_content["search_terms"] or [],
                    "params": {
                        "video_subject": video_subject.value,
                        "video_script": "",
                        "video_terms": None,
                        "video_aspect": video_aspect.value,
                        "video_concat_mode": video_concat_mode.value,
                        "video_transition_mode": None,
                        "video_clip_duration": video_clip_duration.value,
                        "video_count": video_count.value,
                        "video_source": video_source.value,
                        "video_materials": None,
                        "custom_audio_file": None,
                        "video_language": "zh-CN",
                        "voice_name": voice_name.value,
                        "voice_volume": voice_volume.value,
                        "voice_rate": voice_rate.value,
                        "bgm_type": bgm_type.value,
                        "bgm_file": bgm_file.value,
                        "bgm_volume": bgm_volume.value,
                        "subtitle_enabled": subtitle_enabled.value,
                        "subtitle_position": subtitle_position.value,
                        "custom_position": custom_position.value,
                        "font_name": font_name.value,
                        "text_fore_color": text_fore_color.value,
                        "text_background_color": text_background_color.value,
                        "rounded_subtitle_background": rounded_subtitle_background.value,
                        "font_size": font_size.value,
                        "stroke_color": stroke_color.value,
                        "stroke_width": stroke_width.value,
                        "n_threads": n_threads.value,
                        "paragraph_number": 1,
                        "video_script_prompt": "",
                        "custom_system_prompt": "",
                    }
                }
                
                try:
                    with get_db_context() as db:
                        current_user = get_current_user_from_state(db)
                        
                        # 创建任务，将完整的 script.json 存入数据库
                        task_in = VideoTaskCreate(
                            video_source=video_source.value,
                            config_json=json.dumps(script_json, ensure_ascii=False, indent=2),
                            status=0,  # 挂起状态
                        )
                        
                        task = video_task_repo.create(
                            db=db, obj_in=task_in, current_user_id=current_user.id
                        )
                    
                    notifications.show_success(f"任务创建成功！任务 ID: {task.id}")
                    
                except Exception as e:
                    notifications.show_error(f"创建任务失败：{str(e)}")
            
            ui.button("创建任务", icon="add_task", on_click=create_task).props("color=primary size=lg")


def render_task_list_section():
    """渲染任务清单区域"""
    with ui.card().classes('w-full p-6'):
        ui.label("任务清单").classes("text-xl font-bold mb-4")
        
        # 任务列表容器
        task_list_container = ui.column().classes("w-full gap-4")
        
        # 状态徽章颜色映射
        status_colors = {
            0: "gray",    # 挂起
            1: "blue",    # 进行中
            2: "green",   # 成功
            -1: "red",    # 失败
        }
        
        status_labels = {
            0: "挂起",
            1: "进行中",
            2: "成功",
            -1: "失败",
        }
        
        def render_task_item(task):
            """渲染单个任务项"""
            with ui.card().classes("w-full p-4"):
                with ui.row().classes("w-full justify-between items-start"):
                    with ui.column().classes("flex-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(f"任务 ID: {task.id}").classes("text-lg font-bold")
                            status_chip = ui.chip(
                                status_labels.get(task.status, "未知"),
                                color=status_colors.get(task.status, "gray")
                            ).props("text-color=white size=sm")
                            
                            # 视频来源标识
                            source_badge = ui.chip(
                                "Pexels" if task.video_source == "pexels" else "本地",
                                color="blue-200"
                            ).props("text-color=blue-800 size=xs")
                        
                        # 创建时间
                        ui.label(f"创建时间：{task.created_at}").classes("text-sm text-gray-500")
                        
                        # 配置预览
                        try:
                            config = json.loads(task.config_json)
                            video_subject = config.get("params", {}).get("video_subject", "未知")
                            script_preview = config.get("script", "")[:50].replace("\n", " ")
                            if len(config.get("script", "")) > 50:
                                script_preview += "..."
                            
                            ui.label(f"主题：{video_subject}").classes("text-sm font-bold text-gray-700 mt-2")
                            ui.label(f"文案：{script_preview}").classes("text-sm text-gray-600")
                            
                            # 显示更多参数
                            params = config.get("params", {})
                            concat_mode = "顺序" if params.get("video_concat_mode") == "sequential" else "随机"
                            ratio = params.get("video_aspect", "16:9")
                            duration = params.get("video_clip_duration", 5)
                            
                            ui.label(f"拼接：{concat_mode} | 比例：{ratio} | 片段时长：{duration}秒").classes(
                                "text-sm text-gray-600 mt-1"
                            )
                        except:
                            pass
                        
                        # 结果信息
                        if task.result_message:
                            ui.label(f"结果：{task.result_message}").classes(
                                "text-sm text-gray-600 mt-2"
                            )
                        
                        # 输出文件
                        if task.output_file:
                            ui.link("输出", task.output_file).classes(
                                "text-sm text-green-600 mt-2"
                            )
                    
                    # 操作按钮
                    with ui.column().classes("gap-1"):
                        # 查看详情
                        async def show_task_detail():
                            try:
                                config = json.loads(task.config_json)
                                detail_text = json.dumps(config, ensure_ascii=False, indent=2)
                                await ui.dialog(
                                    f"任务详情 - ID: {task.id}",
                                    content=ui.code(detail_text, language="json"),
                                    persistent=True
                                )
                            except:
                                await ui.dialog(
                                    f"任务详情 - ID: {task.id}",
                                    content=ui.label("无法加载任务详情"),
                                    persistent=True
                                )
                        
                        ui.button("详情", icon="visibility", on_click=show_task_detail).props(
                            "flat dense"
                        )
                        
                        # 删除任务
                        with ui.dialog() as confirm_dialog, ui.card():
                            ui.label("确定要删除这个任务吗？")
                            with ui.row().classes("w-full justify-end"):
                                ui.button("取消", on_click=confirm_dialog.close, color="gray-100")
                                ui.button("确定", on_click=lambda: do_delete(confirm_dialog), color="red")

                        async def do_delete(dialog):
                            try:
                                with get_db_context() as db:
                                    current_user = get_current_user_from_state(db)
                                    video_task_repo.remove(db=db, id=task.id)
                                notifications.show_success("任务已删除")
                                dialog.close()
                                await load_tasks()
                            except Exception as e:
                                notifications.show_error(f"删除失败：{str(e)}")

                        ui.button("删除", icon="delete", on_click=confirm_dialog.open).props(
                            "flat dense color=red"
                        )
        
        async def load_tasks():
            """加载任务列表"""
            task_list_container.clear()
            
            try:
                with get_db_context() as db:
                    current_user = get_current_user_from_state(db)
                    tasks = video_task_repo.get_for_user(
                        db=db, current_user_id=current_user.id
                    )
                
                if not tasks:
                    with task_list_container:
                        ui.label("暂无任务记录").classes("text-gray-500 text-center w-full")
                else:
                    for task in tasks:
                        with task_list_container:
                            render_task_item(task)
            except Exception as e:
                notifications.show_error(f"加载任务列表失败：{str(e)}")
        
        # 刷新按钮
        with ui.row().classes("w-full justify-between items-center mb-4"):
            ui.button("刷新列表", icon="refresh", on_click=load_tasks).props("flat")
            
            # 自动刷新开关
            auto_refresh = ui.switch("自动刷新 (5 秒)", value=True)
            
            # 定时器
            refresh_timer = None
            
            def toggle_refresh():
                nonlocal refresh_timer
                if auto_refresh.value:
                    refresh_timer = ui.timer(5.0, load_tasks)
                else:
                    if refresh_timer:
                        refresh_timer.cancel()
            
            auto_refresh.on("update:model-value", toggle_refresh)
            
            # 启动自动刷新
            if auto_refresh.value:
                refresh_timer = ui.timer(5.0, load_tasks)
        
        # 初始加载
        load_tasks()