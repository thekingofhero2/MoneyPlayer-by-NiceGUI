from typing import Optional
from sqlmodel import Field, Relationship, SQLModel

from src.core.config import settings

TABLE_ARGS = {"schema": settings.SCHEMA_NAME}


class UserBase(SQLModel):
    """Establishes the fundamental fields common to all user-related models,
    such as email, is_active, is_superuser, and full_name."""

    email: str = Field(unique=True, index=True)
    is_active: bool = True
    is_superuser: bool = False
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Inherits from UserBase and is used specifically for creating new users.
    It adds a password field that is required only during the user creation process."""

    password: str = Field(min_length=8, max_length=72)


class UserRead(UserBase):
    """Designed for API responses when retrieving user data.
    It includes the user's id but omits sensitive information like the hashed_password to prevent it from being exposed."""

    id: int


class ItemBase(SQLModel):
    """The base model for items, containing the core fields: title and description."""

    title: str
    description: Optional[str] = None


class ItemCreate(ItemBase):
    """Inherits from ItemBase and is used for validating the data when a new item is created."""

    pass


class ItemUpdate(SQLModel):
    """Used for updating an existing item. Its fields (title, description) are optional,
    allowing for partial updates where only the changed fields need to be provided."""

    title: Optional[str] = None
    description: Optional[str] = None


class Item(ItemBase, table=True):
    """The database table model for an item. It includes the ItemBase fields along with an id (primary key) and an owner_id,
    which is a foreign key linking the item to a user. It also defines the relationship back to the User model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    owner_id: Optional[int] = Field(
        default=None, foreign_key=f"{settings.SCHEMA_NAME}.user.id"
    )
    owner: Optional["User"] = Relationship(
        back_populates="items", sa_relationship_kwargs={"foreign_keys": "Item.owner_id"}
    )

    __table_args__ = TABLE_ARGS


class ItemRead(ItemBase):
    """The model for returning item data in API responses, including the item's id and the owner_id."""

    id: int
    owner_id: int


# Video Script Models
class VideoScriptBase(SQLModel):
    """视频文案基础模型"""

    theme: str = Field(..., description="视频主题")
    mode: str = Field(default="monologue", description="文案模式：monologue(独白), dialogue(对话), interview(访谈), story(故事)")
    content: str = Field(..., description="生成的文案内容")
    keywords: Optional[str] = Field(default=None, description="抽取的关键词，JSON 数组格式")


class VideoScriptCreate(VideoScriptBase):
    """创建视频文案的模型"""

    pass


class VideoScript(VideoScriptBase, table=True):
    """视频文案数据库表模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None, foreign_key=f"{settings.SCHEMA_NAME}.user.id"
    )
    owner: Optional["User"] = Relationship(
        back_populates="video_scripts",
        sa_relationship_kwargs={"foreign_keys": "VideoScript.user_id"},
    )
    created_at: Optional[str] = Field(default=None, description="创建时间")

    __table_args__ = TABLE_ARGS


class VideoScriptRead(VideoScriptBase):
    """视频文案响应模型"""

    id: int
    user_id: int
    created_at: Optional[str] = None


# User LLM Configuration Models
class UserLLMConfigBase(SQLModel):
    """用户 LLM 配置基础模型"""

    api_base: str = Field(default="https://api.openai.com/v1", description="API Base URL")
    api_key: str = Field(..., description="API Key")
    model: str = Field(default="gpt-3.5-turbo", description="模型名称")
    max_tokens: int = Field(default=2000, description="最大 token 数")
    temperature: float = Field(default=0.7, description="温度参数")


class UserLLMConfigCreate(UserLLMConfigBase):
    """创建用户 LLM 配置的模型"""

    pass


class UserLLMConfig(UserLLMConfigBase, table=True):
    """用户 LLM 配置数据库表模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None, foreign_key=f"{settings.SCHEMA_NAME}.user.id", unique=True
    )
    user: Optional["User"] = Relationship(
        back_populates="llm_config",
        sa_relationship_kwargs={"foreign_keys": "UserLLMConfig.user_id"},
    )
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

    __table_args__ = TABLE_ARGS


class UserLLMConfigRead(UserLLMConfigBase):
    """用户 LLM 配置响应模型"""

    id: int
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# User Video Production Config Models
class UserVideoConfigBase(SQLModel):
    """用户视频制作配置基础模型"""

    pexels_api_key: Optional[str] = Field(default=None, description="Pexels API Key")
    local_video_dir: Optional[str] = Field(default=None, description="本地视频目录路径")
    
    # TTS 配置
    siliflow_api_key: Optional[str] = Field(default=None, description="硅基流动 API Key")
    mimo_api_key: Optional[str] = Field(default=None, description="小米 Mimo API Key")
    azure_api_key: Optional[str] = Field(default=None, description="Azure 语音 API Key")
    
    # 默认朗读设置
    default_volume: float = Field(default=1.0, description="默认朗读音量 (0-2)")
    default_speed: float = Field(default=1.0, description="默认朗读速度 (0.5-2)")
    default_bgm: Optional[str] = Field(default=None, description="默认背景音乐")
    default_bgm_volume: float = Field(default=0.3, description="默认背景音乐音量 (0-1)")
    
    # 默认字幕设置
    default_font: str = Field(default="Arial", description="默认字体")
    default_font_position: str = Field(default="bottom", description="默认字幕位置：top/middle/bottom")
    default_font_color: str = Field(default="#FFFFFF", description="默认字体颜色")
    default_bg_color: str = Field(default="#000000", description="默认字幕背景颜色")
    default_enable_bg: bool = Field(default=True, description="默认是否启用字幕背景")


class UserVideoConfigCreate(UserVideoConfigBase):
    """创建用户视频制作配置的模型"""

    pass


class UserVideoConfig(UserVideoConfigBase, table=True):
    """用户视频制作配置数据库表模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None, foreign_key=f"{settings.SCHEMA_NAME}.user.id", unique=True
    )
    user: Optional["User"] = Relationship(
        back_populates="video_config",
        sa_relationship_kwargs={"foreign_keys": "UserVideoConfig.user_id"},
    )
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

    __table_args__ = TABLE_ARGS


class UserVideoConfigRead(UserVideoConfigBase):
    """用户视频制作配置响应模型"""

    id: int
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Video Task Models
class VideoTaskBase(SQLModel):
    """视频任务基础模型"""

    # 数据来源配置
    video_source: str = Field(..., description="视频来源：pexels/local")
    
    # 任务配置 JSON
    config_json: str = Field(..., description="任务配置 JSON 字符串")
    
    # 任务状态：0-挂起，1-进行中，2-成功，-1-失败
    status: int = Field(default=0, description="任务状态：0-挂起，1-进行中，2-成功，-1-失败")
    
    # 结果信息
    result_message: Optional[str] = Field(default=None, description="任务结果信息")
    output_file: Optional[str] = Field(default=None, description="输出文件路径")


class VideoTaskCreate(VideoTaskBase):
    """创建视频任务的模型"""

    pass


class VideoTask(VideoTaskBase, table=True):
    """视频任务数据库表模型"""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None, foreign_key=f"{settings.SCHEMA_NAME}.user.id"
    )
    owner: Optional["User"] = Relationship(
        back_populates="video_tasks",
        sa_relationship_kwargs={"foreign_keys": "VideoTask.user_id"},
    )
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

    __table_args__ = TABLE_ARGS


class VideoTaskRead(VideoTaskBase):
    """视频任务响应模型"""

    id: int
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# 更新 User 模型，添加与 UserLLMConfig 和 VideoTask 的关系
class User(UserBase, table=True):
    """This is the primary database table model for a user.
    It includes all fields from UserBase plus the database-specific fields: id (the primary key) and hashed_password.
    It also defines the one-to-many relationship, indicating that a user can own multiple items."""

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner")
    video_scripts: list["VideoScript"] = Relationship(back_populates="owner")
    llm_config: Optional["UserLLMConfig"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "UserLLMConfig.user_id"},
    )
    video_config: Optional["UserVideoConfig"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "UserVideoConfig.user_id"},
    )
    video_tasks: list["VideoTask"] = Relationship(back_populates="owner")

    __table_args__ = TABLE_ARGS
