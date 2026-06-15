from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from src.db.session import get_db_context
from src.models import VideoScriptCreate, VideoScriptRead, UserLLMConfigCreate, UserLLMConfigRead
from src.repositories.video_script import video_script_repo
from src.repositories.user_llm_config import user_llm_config_repo
from src.services.llm_service import get_llm_service_for_current_user
from src.frontend.components.auth_utils import get_current_user_from_state
from src.db.session import get_db_context as get_db


router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    """文案生成请求模型"""

    theme: str
    mode: str = "monologue"
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class ScriptUpdateRequest(BaseModel):
    """文案更新请求模型"""

    theme: Optional[str] = None
    mode: Optional[str] = None
    content: Optional[str] = None
    keywords: Optional[str] = None


@router.post("/video-scripts/generate", response_model=VideoScriptRead)
async def generate_script(request: ScriptGenerateRequest):
    """生成视频文案并保存到数据库"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)

            # 获取当前用户的 LLM 服务
            llm_service = get_llm_service_for_current_user()

            # 生成文案
            content = ""
            async for chunk in llm_service.generate_script(
                theme=request.theme, mode=request.mode
            ):
                content += chunk

            if not content.strip():
                raise HTTPException(status_code=400, detail="生成的文案为空")

            # 抽取关键词
            try:
                keywords = await llm_service.extract_keywords(content)
                keywords_json = ",".join(keywords)
            except Exception as e:
                keywords_json = None

            # 保存到数据库
            script_in = VideoScriptCreate(
                theme=request.theme,
                mode=request.mode,
                content=content,
                keywords=keywords_json,
            )
            script = video_script_repo.create(
                db=db, obj_in=script_in, current_user_id=current_user.id
            )

            return script

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成文案失败：{str(e)}")


@router.get("/video-scripts", response_model=list[VideoScriptRead])
async def get_video_scripts(skip: int = 0, limit: int = 100):
    """获取用户的视频文案列表"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            scripts = video_script_repo.get_for_user(
                db=db, current_user_id=current_user.id, skip=skip, limit=limit
            )
            return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文案列表失败：{str(e)}")


@router.get("/video-scripts/{script_id}", response_model=VideoScriptRead)
async def get_video_script(script_id: int):
    """获取单个视频文案"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            script = video_script_repo.get_by_id(db=db, script_id=script_id)

            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")

            if script.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权访问此文案")

            return script
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文案失败：{str(e)}")


@router.put("/video-scripts/{script_id}", response_model=VideoScriptRead)
async def update_video_script(script_id: int, request: ScriptUpdateRequest):
    """更新视频文案"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            script = video_script_repo.get_by_id(db=db, script_id=script_id)

            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")

            if script.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权访问此文案")

            update_data = request.model_dump(exclude_unset=True)
            updated_script = video_script_repo.update(
                db=db, db_obj=script, obj_in=update_data
            )
            return updated_script
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新文案失败：{str(e)}")


@router.delete("/video-scripts/{script_id}")
async def delete_video_script(script_id: int):
    """删除视频文案"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            script = video_script_repo.get_by_id(db=db, script_id=script_id)

            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")

            if script.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权访问此文案")

            video_script_repo.delete(db=db, script_id=script_id)
            return {"message": "文案已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文案失败：{str(e)}")


@router.post("/video-scripts/extract-keywords/{script_id}")
async def extract_keywords_for_script(script_id: int):
    """重新抽取文案关键词"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            script = video_script_repo.get_by_id(db=db, script_id=script_id)

            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")

            if script.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权访问此文案")

            # 获取当前用户的 LLM 服务
            llm_service = get_llm_service_for_current_user()

            keywords = await llm_service.extract_keywords(script.content)
            keywords_json = ",".join(keywords)

            updated_script = video_script_repo.update(
                db=db, db_obj=script, obj_in={"keywords": keywords_json}
            )
            return {"keywords": keywords, "script": updated_script}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"抽取关键词失败：{str(e)}")


# User LLM Configuration Endpoints
@router.get("/user-llm-config", response_model=Optional[UserLLMConfigRead])
async def get_user_llm_config():
    """获取用户的 LLM 配置"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            config = user_llm_config_repo.get_for_user(
                db=db, current_user_id=current_user.id
            )
            return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败：{str(e)}")


@router.post("/user-llm-config", response_model=UserLLMConfigRead)
async def save_user_llm_config(request: UserLLMConfigCreate):
    """保存用户的 LLM 配置"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            config = user_llm_config_repo.create_or_update(
                db=db, obj_in=request, current_user_id=current_user.id
            )
            return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败：{str(e)}")


@router.delete("/user-llm-config")
async def delete_user_llm_config():
    """删除用户的 LLM 配置"""
    try:
        with get_db() as db:
            current_user = get_current_user_from_state(db)
            user_llm_config_repo.delete(db=db, current_user_id=current_user.id)
            return {"message": "配置已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败：{str(e)}")
