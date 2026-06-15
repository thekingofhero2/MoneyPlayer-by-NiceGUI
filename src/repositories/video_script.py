from typing import Optional
from sqlmodel import Session, select
from src.models import VideoScript, VideoScriptCreate
from datetime import datetime


class VideoScriptRepository:
    """视频文案仓库类"""

    def create(
        self, *, db: Session, obj_in: VideoScriptCreate, current_user_id: int
    ) -> VideoScript:
        """创建新的视频文案"""
        db_obj = VideoScript(
            **obj_in.model_dump(),
            user_id=current_user_id,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_id(self, *, db: Session, script_id: int) -> Optional[VideoScript]:
        """根据 ID 获取视频文案"""
        return db.get(VideoScript, script_id)

    def get_for_user(
        self, *, db: Session, current_user_id: int, skip: int = 0, limit: int = 100
    ) -> list[VideoScript]:
        """获取用户的视频文案列表"""
        statement = (
            select(VideoScript)
            .where(VideoScript.user_id == current_user_id)
            .offset(skip)
            .limit(limit)
        )
        results = db.exec(statement)
        return results.all()

    def update(
        self, *, db: Session, db_obj: VideoScript, obj_in: dict
    ) -> VideoScript:
        """更新视频文案"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, *, db: Session, script_id: int) -> None:
        """删除视频文案"""
        db_obj = db.get(VideoScript, script_id)
        if db_obj:
            db.delete(db_obj)
            db.commit()


video_script_repo = VideoScriptRepository()
