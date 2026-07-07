import asyncio
import json
import httpx
from contextlib import asynccontextmanager
from nicegui import ui, app
import re
from src.frontend.layouts.default import dashboard_frame
from src.frontend.components import notifications
from src.frontend.components.auth_utils import get_current_user_from_state
from src.db.session import get_db_context
from src.repositories.video_script import video_script_repo
from src.repositories.user_llm_config import user_llm_config_repo
from src.services.llm_service import get_llm_service_for_current_user
from src.utils.tools import filter_think_tags


# ============== 通用工具函数 ==============

def parse_keywords(text: str) -> list[str]:
    """解析关键词文本，返回关键词列表"""
    keywords = re.split(r"[,，\n]", text)
    keywords = [kw.strip() for kw in keywords if kw.strip()]
    return keywords[:10]


@asynccontextmanager
async def button_loading(btn):
    """按钮 loading 状态的上下文管理器"""
    btn.disable()
    btn.icon = "none"
    btn._props['spinner'] = True
    btn.update()
    try:
        yield
    finally:
        btn.enable()
        btn.icon = "auto_awesome"
        btn._props.pop('spinner', None)
        btn.update()


def get_current_user():
    """获取当前用户"""
    with get_db_context() as db:
        return get_current_user_from_state(db)



@ui.page("/video-scripts")
def video_scripts_page():
    """视频文案生成页面"""
    # 历史记录相关变量
    history_container = None
    mode_filter = None
    
    async def load_history_scripts():
        """加载历史记录"""
        nonlocal history_container, mode_filter
        if history_container is None:
            return
            
        history_container.clear()

        try:
            with get_db_context() as db:
                current_user = get_current_user_from_state(db)
                scripts = video_script_repo.get_for_user(
                    db=db, current_user_id=current_user.id
                )

            # 筛选
            if mode_filter and mode_filter.value != "all":
                scripts = [s for s in scripts if s.mode == mode_filter.value]

            # 按时间倒序
            scripts = sorted(scripts, key=lambda x: x.created_at or "", reverse=True)

            with history_container:
                if not scripts:
                    ui.label("暂无历史记录").classes("text-gray-500 text-center w-full")
                else:
                    for script in scripts:
                        render_history_item(script)

        except Exception as e:
            notifications.show_error(f"加载历史记录失败：{str(e)}")
    
    def render_history_item(script):
        """渲染单个历史记录项"""
        with ui.card().classes("w-full p-4"):
            with ui.row().classes("w-full justify-between items-start"):
                with ui.column().classes("flex-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(script.theme).classes("text-lg font-bold")
                        mode_badge = ui.chip(
                            {
                                "monologue": "独白",
                                "dialogue": "对话",
                                "interview": "访谈",
                                "story": "故事",
                            }.get(script.mode, script.mode)
                        ).props("color=blue text-color=white size=sm")
                        ui.label(f"创建时间：{script.created_at}").classes(
                            "text-sm text-gray-500"
                        )

                    # 内容预览
                    preview = script.content[:200] + "..." if len(script.content) > 200 else script.content
                    ui.label(preview).classes("text-gray-700 mt-2")

                    # 关键词
                    if script.keywords:
                        keywords = script.keywords.split(",")[:5]
                        with ui.row().classes("mt-2 gap-1"):
                            for kw in keywords:
                                ui.chip(kw.strip()).props(
                                    "color=gray-200 text-color=gray-700 size=xs"
                                )

                with ui.column().classes("gap-1"):
                    # 查看按钮
                    async def show_detail():
                        await show_script_detail(script)

                    ui.button("查看", icon="visibility", on_click=show_detail).props(
                        "flat dense"
                    )

                    # 删除按钮
                    async def delete_script():
                        with ui.dialog() as delete_dialog, delete_dialog:
                            with ui.card():
                                ui.label("确定要删除这个文案吗？")
                                with ui.row():
                                    ui.button("确定", on_click=delete_dialog.submit)
                                    ui.button("取消", on_click=delete_dialog.close)
                                    
                        if await delete_dialog:
                            try:
                                with get_db_context() as db:
                                    current_user = get_current_user_from_state(db)
                                    video_script_repo.delete(
                                        db=db, script_id=script.id
                                    )
                                notifications.show_success("已删除")
                                await load_history_scripts()
                            except Exception as e:
                                notifications.show_error(f"删除失败：{str(e)}")

                    ui.button("删除", icon="delete", on_click=delete_script).props(
                        "flat dense color=red"
                    )
    
    def render_history_section_inner():
        """渲染历史记录区域"""
        ui.label("历史记录").classes("text-xl font-bold mb-4")

        # 筛选器
        with ui.row().classes("w-full justify-between items-center mb-4"):
            nonlocal mode_filter
            mode_filter = ui.select(
                {
                    "all": "全部",
                    "monologue": "独白",
                    "dialogue": "对话",
                    "interview": "访谈",
                    "story": "故事",
                },
                value="all",
                label="模式筛选",
            ).classes("w-40")

            refresh_btn = ui.button(icon="refresh", on_click=lambda: load_history_scripts()).props(
                "flat round"
            )

        # 历史记录列表
        nonlocal history_container
        history_container = ui.column().classes("w-full gap-2")
        
        # 筛选变化时重新加载
        mode_filter.on("update:model-value", lambda _: load_history_scripts())

        # 初始加载
        ui.timer(0.1, lambda: load_history_scripts(), once=True)
    
    with dashboard_frame(title="视频文案生成"):
        # 主容器
        with ui.column().classes("w-full max-w-6xl gap-4"):
            # 顶部配置区域
            with ui.expansion("LLM 配置", icon="settings").classes("w-full"):
                render_config_section()

            # 生成区域
            with ui.card().classes("w-full p-6"):
                render_generation_section(load_history_scripts)

            # 历史记录区域
            with ui.card().classes("w-full p-6"):
                render_history_section_inner()


def render_config_section():
    """渲染配置区域"""
    # 默认配置
    default_config = {
        "api_base": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-3.5-turbo",
        "max_tokens": 2000,
        "temperature": 0.7,
    }

    with ui.grid().classes("w-full grid-cols-1 md:grid-cols-3 gap-4"):
        api_base_input = ui.input(
            "API Base URL",
            value=default_config["api_base"],
            placeholder="https://api.openai.com/v1",
        ).classes("w-full")
        api_key_input = ui.input(
            "API Key",
            value="",
            placeholder="sk-...",
            password=True,
        ).classes("w-full")
        model_input = ui.input(
            "模型名称",
            value=default_config["model"],
            placeholder="gpt-3.5-turbo",
        ).classes("w-full")

    # 从数据库加载用户配置
    async def load_user_config():
        """从数据库加载用户配置"""
        try:
            with get_db_context() as db:
                current_user = get_current_user_from_state(db)
                config = user_llm_config_repo.get_for_user(
                    db=db, current_user_id=current_user.id
                )
                if config:
                    api_base_input.value = config.api_base
                    api_key_input.value = config.api_key
                    model_input.value = config.model
        except Exception:
            pass  # 如果加载失败，使用默认值

    # 页面加载时自动加载配置
    ui.timer(0.1, lambda: load_user_config(), once=True)

    with ui.row().classes("w-full justify-end mt-4 gap-2"):
        async def test_config():
            """测试配置"""
            if not api_base_input.value or not api_key_input.value:
                notifications.show_error("请填写 API Base 和 API Key")
                return

            try:
                # 直接调用用户配置的 OpenAI 接口进行测试
                async with httpx.AsyncClient(timeout=10.0) as client:
                    url = f"{api_base_input.value}/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {api_key_input.value}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": model_input.value,
                        "messages": [
                            {"role": "user", "content": "Hello, this is a test."}
                        ],
                        "max_tokens": 10,
                    }
                    response = await client.post(url, json=payload, headers=headers)
                    
                    if response.status_code != 200:
                        error_msg = f"HTTP {response.status_code}"
                        try:
                            error_data = response.json()
                            if "error" in error_data:
                                error_msg = error_data["error"].get("message", error_msg)
                        except:
                            pass
                        notifications.show_error(f"配置测试失败：{error_msg}")
                        return

                notifications.show_success("配置测试成功！")
            except httpx.ConnectError as e:
                notifications.show_error(f"无法连接到 API 服务器：{str(e)}")
            except httpx.TimeoutException as e:
                notifications.show_error(f"请求超时：{str(e)}")
            except Exception as e:
                notifications.show_error(f"测试失败：{str(e)}")

        async def save_config_async():
            """异步保存配置到数据库"""
            if not api_base_input.value or not api_key_input.value:
                notifications.show_error("API Base 和 API Key 不能为空")
                return

            try:
                with get_db_context() as db:
                    current_user = get_current_user_from_state(db)
                    from src.models import UserLLMConfigCreate
                    config_in = UserLLMConfigCreate(
                        api_base=api_base_input.value,
                        api_key=api_key_input.value,
                        model=model_input.value,
                    )
                    config = user_llm_config_repo.create_or_update(
                        db=db, obj_in=config_in, current_user_id=current_user.id
                    )
                notifications.show_success("配置已保存到数据库！")
            except Exception as e:
                notifications.show_error(f"保存失败：{str(e)}")

        ui.button("测试配置", on_click=test_config, icon="check").props(
            "color=blue flat"
        )
        ui.button("保存配置", on_click=save_config_async, icon="save").props(
            "color=primary"
        )


def render_generation_section(load_history_scripts_callback):
    """渲染生成区域"""
    ui.label("创作新文案").classes("text-xl font-bold mb-4")

    with ui.grid().classes("w-full grid-cols-1 md:grid-cols-2 gap-4"):
        # 主题输入
        theme_input = (
            ui.textarea("视频主题")
            .classes("w-full col-span-2")
            .props("rows=3 placeholder='例如：人工智能的未来发展'")
        )

        # 模式选择
        mode_select = ui.select(
            {
                "monologue": "独白",
                "dialogue": "对话",
                "interview": "访谈",
                "story": "故事",
            },
            value="monologue",
            label="文案模式",
        ).classes("w-full")

        # 模式说明
        mode_description = ui.markdown(
            """**独白**: 单人讲述，适合知识分享、观点表达
**对话**: 双人对话，适合讨论、辩论
**访谈**: 主持人和嘉宾问答，适合深度探讨
**故事**: 叙事性内容，适合情感共鸣"""
        ).classes("w-full col-span-2 text-sm text-gray-600")

    # 生成按钮
    with ui.row().classes("w-full justify-end mt-4"):
        generate_btn = ui.button("生成文案", icon="auto_awesome").props(
            "color=primary size=lg"
        )

    # 生成状态显示
    with ui.card().classes("w-full mt-4") as status_card:
        status_card.set_visibility(False)
        with ui.row().classes("w-full items-center"):
            ui.spinner("dots", size="md").classes("mr-2")
            status_label = ui.label("正在生成文案...")

    # 文案编辑和预览区域（左右分栏）
    with ui.row().classes("w-full mt-4 gap-4"):
        # 左侧：编辑区域
        with ui.card().classes("w-1/3 p-4"):
            ui.label("编辑文案").classes("text-lg font-bold mb-2")
            content_editor = (
                ui.textarea()
                .classes("w-full")
                .props("outlined rows=10 placeholder='在此编辑文案内容...'")
                .style("min-height: 300px; font-family: monospace;")
            )
            
            # 编辑提示
            ui.label("💡 提示：支持 Markdown 语法，右侧实时预览").classes(
                "text-sm text-gray-500 mt-2"
            )

        # 右侧：Markdown 预览区域
        with ui.card().classes("w-1/3 p-4"):
            ui.label("Markdown 预览").classes("text-lg font-bold mb-2")
            content_display = (
                ui.markdown("")
                .classes("w-full")
                .style("min-height: 300px; white-space: pre-wrap; background: #f5f5f5; padding: 12px; border-radius: 4px;")
                .bind_content_from(content_editor,"value")
            )

    # # 监听编辑内容变化，实时更新预览
    # def update_preview():
    #     """更新 Markdown 预览"""
    #     content_display.content = content_editor.value or ""

    # content_editor.on("update:model-value", update_preview)

    # 关键词编辑区域
    with ui.card().classes("w-full mt-4 p-4") as keyword_card:
        #keyword_card.set_visibility(False)
        ui.label("关键词").classes("text-lg font-bold mb-2")
        
        # 关键词输入框
        keywords_input = (
            ui.input("关键词，用逗号分隔")
            .classes("w-full")
            .props("outlined dense")
        )
        
        # 关键词操作按钮
        with ui.row().classes("mt-2 gap-2"):
            extract_btn = ui.button("抽取关键词", icon="auto_awesome").props(
                "color=primary flat size=sm"
            )
            clear_btn = ui.button("清空", icon="clear").props(
                "color=grey flat size=sm"
            )

    # 保存按钮
    save_btn = ui.button("保存到历史记录", icon="save").props("color=success").classes("mt-4")
    save_btn.set_visibility(False)

    
    
    # 生成处理函数
    async def handle_generate():
        """处理生成请求"""
        if not theme_input.value.strip():
            notifications.show_error("请输入视频主题")
            return

        # 获取当前用户的 LLM 服务
        llm_service = get_llm_service_for_current_user()

        # 检查 API Key
        if not llm_service.api_key:
            notifications.show_error("请先配置 API Key")
            return

        # 显示状态卡片
        status_card.visible = True
        content_editor.value = ""
        keyword_card.visible = False
        save_btn.visible = False
        generate_btn.disable()

        try:
            
            # 生成文案
            content = ""
            async for chunk in llm_service.generate_script(
                theme=theme_input.value, mode=mode_select.value,
            ):
                content += chunk
                # 实时更新编辑器显示
                content_editor.value = content + "▌"
                await asyncio.sleep(0.05)
            
            content = filter_think_tags(content)
            content_editor.value = content

            # 显示关键词卡片
            keyword_card.visible = True
            
            # 抽取关键词
            try:
                keywords_text = filter_think_tags(
                    await llm_service.extract_keywords(content)
                )
                keywords_input.value = ", ".join(parse_keywords(keywords_text))
            except Exception:
                keywords_input.value = ""
            
            # 保存到数据库
            from src.models import VideoScriptCreate
            with get_db_context() as db:
                current_user = get_current_user_from_state(db)
                video_script_repo.create(
                    db=db,
                    obj_in=VideoScriptCreate(
                        theme=theme_input.value,
                        mode=mode_select.value,
                        content=content,
                        keywords=keywords_input.value,
                    ),
                    current_user_id=current_user.id,
                )
            
            notifications.show_success("文案生成成功！")
            save_btn.visible = True
            await load_history_scripts_callback()

        except Exception as e:
            notifications.show_error(f"生成失败：{str(e)}")
            status_label.text = "生成失败"
        finally:
            status_card.visible = False
            generate_btn.enable()

    generate_btn.on("click", handle_generate)

    # 关键词抽取按钮处理
    async def handle_extract_keywords():
        """处理关键词抽取"""
        if not content_editor.value.strip():
            notifications.show_error("请先生成文案内容")
            return

        llm_service = get_llm_service_for_current_user()
        try:
            async with button_loading(extract_btn):
                keywords_text = filter_think_tags(
                    await llm_service.extract_keywords(content_editor.value)
                )
                keywords_input.value = ", ".join(parse_keywords(keywords_text))
                notifications.show_success("关键词抽取成功！")
        except Exception as e:
            notifications.show_error(f"抽取失败：{str(e)}")

    extract_btn.on("click", handle_extract_keywords)

    # 清空关键词按钮处理
    def handle_clear_keywords():
        """清空关键词"""
        keywords_input.value = ""

    clear_btn.on("click", handle_clear_keywords)


async def show_script_detail(script):
    """显示文案详情"""
    with ui.dialog() as dialog, ui.card().classes("min-w-[800px] max-w-[1000px]"):
        ui.label("文案详情").classes("text-xl font-bold mb-4")

        with ui.column().classes("w-full gap-2"):
            ui.label(f"主题：{script.theme}").classes("font-bold")
            ui.label(f"模式：{script.mode}").classes("text-sm")
            ui.label(f"创建时间：{script.created_at}").classes("text-sm text-gray-500")

            ui.separator()

            ui.label("文案内容:").classes("font-bold mt-2")
            
            # 左右分栏：编辑和预览
            with ui.row().classes("w-full gap-4"):
                # 左侧编辑
                with ui.column().classes("w-1/2"):
                    ui.label("编辑").classes("font-bold mb-2")
                    content_editor = (
                        ui.textarea()
                        .classes("w-full")
                        .props("outlined rows=15")
                        .style("min-height: 300px; font-family: monospace;")
                    )
                    content_editor.value = script.content
                    
                    def update_preview():
                        content_display.content = content_editor.value or ""
                    
                    content_editor.on("update:model-value", update_preview)

                # 右侧预览
                with ui.column().classes("w-1/2"):
                    ui.label("Markdown 预览").classes("font-bold mb-2")
                    content_display = (
                        ui.markdown("")
                        .classes("w-full")
                        .style("min-height: 300px; white-space: pre-wrap; background: #f5f5f5; padding: 12px; border-radius: 4px;")
                    )
                    content_display.content = script.content

            ui.separator()
            ui.label("关键词:").classes("font-bold")
            
            # 关键词编辑框
            keywords_input = ui.input("关键词，用逗号分隔", value=script.keywords or "").classes("w-full")
            
            # 关键词操作按钮
            with ui.row().classes("gap-2"):
                async def extract_keywords_handler():
                    """抽取关键词"""
                    llm_service = get_llm_service_for_current_user()
                    try:
                        async with button_loading(extract_btn):
                            keywords_text = filter_think_tags(
                                await llm_service.extract_keywords(content_editor.value)
                            )
                            keywords_input.value = ", ".join(parse_keywords(keywords_text))
                            notifications.show_success("关键词抽取成功！")
                    except Exception as e:
                        notifications.show_error(f"抽取失败：{str(e)}")
                
                extract_btn = ui.button("抽取关键词", icon="auto_awesome").props(
                    "color=primary flat size=sm"
                )
                extract_btn.on("click", extract_keywords_handler)
                
                ui.button("清空", icon="clear").props(
                    "color=grey flat size=sm"
                ).on("click", lambda: keywords_input.set_value(""))

            ui.separator()

            with ui.row().classes("w-full justify-between mt-4"):
                async def save_changes():
                    """保存修改"""
                    try:
                        with get_db_context() as db:
                            current_user = get_current_user_from_state(db)
                            updated_script = video_script_repo.update(
                                db=db,
                                db_obj=script,
                                obj_in={
                                    "content": content_editor.value,
                                    "keywords": keywords_input.value,
                                },
                            )
                        notifications.show_success("修改已保存！")
                        script.content = updated_script.content
                        script.keywords = updated_script.keywords
                        await load_history_scripts()
                    except Exception as e:
                        notifications.show_error(f"保存失败：{str(e)}")
                
                ui.button("保存修改", icon="save", on_click=save_changes).props(
                    "color=success flat"
                )
                ui.button("关闭", on_click=dialog.close).props("flat")

    dialog.open()
