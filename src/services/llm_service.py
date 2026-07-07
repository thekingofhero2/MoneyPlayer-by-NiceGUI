import httpx
import json
import re
from typing import Optional, AsyncGenerator
from src.core.llm_config import llm_settings
from src.db.session import get_db_context
from src.frontend.components.auth_utils import get_current_user_from_state
from src.repositories.user_llm_config import user_llm_config_repo


class LLMService:
    """LLM 服务类，用于调用大模型生成文案和抽取关键词"""

    def __init__(self, api_base: str = None, api_key: str = None, model: str = None, 
                 max_tokens: int = 2000, temperature: float = 0.7):
        # 如果没有提供配置，使用默认配置
        if api_base is None:
            self.api_base = llm_settings.llm_api_base
        else:
            self.api_base = api_base
            
        if api_key is None:
            self.api_key = llm_settings.llm_api_key
        else:
            self.api_key = api_key
            
        if model is None:
            self.model = llm_settings.llm_model
        else:
            self.model = model
            
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_system_prompt(self, mode: str) -> str:
        """根据模式获取系统提示词"""
        prompts = {
            "monologue": """# Role: Video Script Generator

## Goals:
Generate a script for a video, depending on the subject of the video.

## Constrains:
1. the script is to be returned as a string with the specified number of paragraphs.
2. do not under any circumstance reference this prompt in your response.
3. get straight to the point, don't start with unnecessary things like, "welcome to this video".
4. you must not include any type of markdown or formatting in the script, never use a title.
5. only return the raw content of the script.
6. do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line.
7. you must not mention the prompt, or anything about the script itself. also, never talk about the amount of paragraphs or lines. just write the script.
8. respond in the same language as the video subject.""",
            "dialogue": """你是一个专业的视频文案创作者。请根据用户提供的主题，创作一段自然流畅的对话式视频文案。
要求：
1. 设计 2 个角色进行对话
2. 对话要自然，符合日常交流习惯
3. 通过对话逐步展开主题
4. 要有适当的互动和情绪表达
5. 适合 1-3 分钟的视频时长""",
            "interview": """你是一个专业的视频文案创作者。请根据用户提供的主题，创作一段访谈式视频文案。
要求：
1. 设计主持人和嘉宾两个角色
2. 主持人提问要专业且引导性强
3. 嘉宾回答要有深度和见解
4. 通过问答形式深入探讨主题
5. 适合 2-5 分钟的视频时长""",
            "story": """你是一个专业的视频文案创作者。请根据用户提供的主题，创作一个故事性的视频文案。
要求：
1. 有清晰的故事情节（起因、经过、高潮、结局）
2. 要有冲突或转折，增加戏剧性
3. 语言生动形象，有画面感
4. 能引发观众情感共鸣
5. 适合 2-5 分钟的视频时长""",
        }
        return prompts.get(mode, prompts["monologue"])

    async def generate_script(
        self, theme: str, mode: str = "monologue"
    ) -> AsyncGenerator[str, None]:
        """异步生成视频文案，流式返回"""
        system_prompt = self._get_system_prompt(mode)
        user_prompt = f"请为以下主题创作视频文案：{theme}"

        url = f"{self.api_base}/chat/completions"
        headers = self._get_headers()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API 请求失败：{response.status_code} - {error_text.decode()}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if (
                                "choices" in chunk
                                and len(chunk["choices"]) > 0
                                and "delta" in chunk["choices"][0]
                            ):
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

    async def extract_keywords(self, text: str) -> list[str]:
        """从文案中抽取关键词"""
        system_prompt = """你是一个专业的文本分析专家。请从给定的文案中抽取 5-10 个关键词。
要求：
1. 关键词要能准确概括文案的核心内容
2. 只返回关键词列表，用逗号分隔
3. 不要包含任何解释或其他文字"""

        url = f"{self.api_base}/chat/completions"
        headers = self._get_headers()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请从以下文案中抽取关键词：\n\n{text}"},
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise Exception(f"API 请求失败：{response.status_code}")

            result = response.json()
            keywords_text = result["choices"][0]["message"]["content"].strip()
            return keywords_text
            


def get_llm_service_for_current_user() -> LLMService:
    """根据当前用户配置创建 LLMService 实例"""
    try:
        with get_db_context() as db:
            current_user = get_current_user_from_state(db)
            config = user_llm_config_repo.get_for_user(
                db=db, current_user_id=current_user.id
            )
            
            if config:
                # 使用用户配置的参数
                return LLMService(
                    api_base=config.api_base,
                    api_key=config.api_key,
                    model=config.model,
                    max_tokens=getattr(config, 'max_tokens', 2000),
                    temperature=getattr(config, 'temperature', 0.7),
                )
    except Exception:
        # 如果获取用户配置失败，使用默认配置
        pass
    
    # 返回默认配置的实例
    return LLMService()
