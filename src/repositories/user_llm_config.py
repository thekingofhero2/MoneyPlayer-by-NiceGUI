from typing import Optional
from sqlmodel import Session, select
from src.models import UserLLMConfig, UserLLMConfigCreate, UserLLMConfigRead
from datetime import datetime


class UserLLMConfigRepository:
    """用户 LLM 配置仓库类"""

    def create_or_update(
        self, *, db: Session, obj_in: UserLLMConfigCreate, current_user_id: int
    ) -> UserLLMConfig:
        """创建或更新用户 LLM 配置"""
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
            db_obj = UserLLMConfig(
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
    ) -> Optional[UserLLMConfig]:
        """获取用户的 LLM 配置"""
        statement = select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user_id
        )
        results = db.exec(statement)
        return results.first()

    def delete(self, *, db: Session, current_user_id: int) -> None:
        """删除用户的 LLM 配置"""
        config = self.get_for_user(db=db, current_user_id=current_user_id)
        if config:
            db.delete(config)
            db.commit()


user_llm_config_repo = UserLLMConfigRepository()
