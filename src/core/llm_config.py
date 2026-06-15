from pydantic_settings import BaseSettings
from typing import Optional


class LLMSettings(BaseSettings):
    """LLM 配置设置"""

    # OpenAI 兼容配置
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-3.5-turbo"

    # 文案生成配置
    default_mode: str = "monologue"  # monologue, dialogue, interview, story
    max_tokens: int = 2000
    temperature: float = 0.7

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略额外的环境变量


llm_settings = LLMSettings()
