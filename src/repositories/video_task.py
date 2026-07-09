from typing import Optional, List
from sqlmodel import Session, select
from src.models import VideoTask, VideoTaskCreate, VideoTaskRead, UserVideoConfig, UserVideoConfigCreate
from src.app_videomaker.utils import utils
from datetime import datetime


class VideoTaskRepository:
    """视频任务仓库类"""

    def create(
        self, *, db: Session, obj_in: VideoTaskCreate, current_user_id: int
    ) -> VideoTask:
        """创建新的视频任务"""
        db_obj = VideoTask(
            **dict(obj_in),
            #task_uuid=utils.get_uuid(),
            user_id=current_user_id,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_for_user(
        self, *, db: Session, current_user_id: int
    ) -> List[VideoTask]:
        """获取用户的视频任务列表"""
        statement = select(VideoTask).where(
            VideoTask.user_id == current_user_id
        ).order_by(VideoTask.created_at.desc())
        results = db.exec(statement)
        return results.all()

    def get(self, db: Session, id: int) -> Optional[VideoTask]:
        """根据 ID 获取视频任务"""
        return db.get(VideoTask, id)

    def update(self, db: Session, *, db_obj: VideoTask, obj_in: dict) -> VideoTask:
        """更新视频任务"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_status(
        self, db: Session, *, task_id: int, status: int, 
        result_message: Optional[str] = None, output_file: Optional[str] = None
    ) -> VideoTask:
        """更新任务状态"""
        task = self.get(db, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        if result_message:
            task.result_message = result_message
        if output_file:
            task.output_file = output_file
        task.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def remove(self, db: Session, *, id: int) -> bool:
        """删除视频任务"""
        task = db.get(VideoTask, id)
        if task:
            db.delete(task)
            db.commit()
            return True
        return False


class UserVideoConfigRepository:
    """用户视频制作配置仓库类"""

    def create_or_update(
        self, *, db: Session, obj_in: UserVideoConfigCreate, current_user_id: int
    ) -> UserVideoConfig:
        """创建或更新用户视频制作配置"""
        # 查找是否已存在该用户的配置
        existing_config = self.get_for_user(db=db, current_user_id=current_user_id)

        if existing_config:
            # 更新现有配置
            for field, value in dict(obj_in).items():
                setattr(existing_config, field, value)
            existing_config.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.add(existing_config)
            db.commit()
            db.refresh(existing_config)
            return existing_config
        else:
            # 创建新配置
            db_obj = UserVideoConfig(
                **dict(obj_in),
                user_id=current_user_id,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj

    def get_for_user(
        self, *, db: Session, current_user_id: int
    ) -> Optional[UserVideoConfig]:
        """获取用户的视频制作配置"""
        statement = select(UserVideoConfig).where(
            UserVideoConfig.user_id == current_user_id
        )
        results = db.exec(statement)
        return results.first()

    def delete(self, *, db: Session, current_user_id: int) -> None:
        """删除用户的视频制作配置"""
        config = self.get_for_user(db=db, current_user_id=current_user_id)
        if config:
            db.delete(config)
            db.commit()


video_task_repo = VideoTaskRepository()
user_video_config_repo = UserVideoConfigRepository()
