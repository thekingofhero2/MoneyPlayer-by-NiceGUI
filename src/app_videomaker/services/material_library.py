"""
本地素材库服务
使用 ChromaDB 存储视频素材元数据，支持按标签（search_term）检索
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from loguru import logger

from src.app_videomaker.utils import utils

# ChromaDB 客户端实例（单例）
_chroma_client = None
_collection_name = "video_materials"


def _get_chroma_client() -> chromadb.PersistentClient:
    """获取 ChromaDB 客户端（单例模式）"""
    global _chroma_client
    if _chroma_client is None:
        storage_dir = utils.storage_dir("chromadb", create=True)
        _chroma_client = chromadb.PersistentClient(
            path=storage_dir,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client


def _get_collection():
    """获取或创建素材集合"""
    client = _get_chroma_client()
    try:
        return client.get_collection(name=_collection_name)
    except Exception:
        return client.create_collection(
            name=_collection_name,
            metadata={"description": "Local video material library"}
        )


def add_video_material(
    video_path: str,
    search_term: str,
    provider: str = "pexels",
    duration: int = 0,
    metadata: Optional[Dict] = None
) -> bool:
    """
    添加视频素材到本地素材库

    Args:
        video_path: 视频文件路径
        search_term: 搜索关键词/标签
        provider: 素材来源 (pexels/pixabay)
        duration: 视频时长（秒）
        metadata: 其他元数据

    Returns:
        是否添加成功
    """
    try:
        collection = _get_collection()

        # 生成唯一 ID
        video_id = f"{search_term}_{os.path.basename(video_path)}"

        # 准备元数据
        meta = {
            "video_path": video_path,
            "search_term": search_term,
            "provider": provider,
            "duration": duration,
            "file_name": os.path.basename(video_path),
            "file_size": os.path.getsize(video_path) if os.path.exists(video_path) else 0,
        }
        if metadata:
            meta.update(metadata)

        # 添加到 ChromaDB
        collection.add(
            ids=[video_id],
            documents=[f"Video material for {search_term}"],
            metadatas=[meta]
        )

        logger.info(f"Added video to material library: {video_id}, search_term: {search_term}")
        return True

    except Exception as e:
        logger.error(f"Failed to add video to material library: {str(e)}")
        return False


def search_materials_by_keyword(keyword: str, limit: int = 50) -> List[Dict]:
    """
    根据关键词搜索本地素材库

    Args:
        keyword: 搜索关键词
        limit: 返回数量限制

    Returns:
        素材列表
    """
    try:
        collection = _get_collection()

        # 使用 where 查询搜索
        results = collection.get(
            where={"search_term": {"$contains": keyword}},
            limit=limit
        )

        materials = []
        for i, metadata in enumerate(results.get("metadatas", [])):
            materials.append({
                "id": results["ids"][i],
                "video_path": metadata.get("video_path", ""),
                "search_term": metadata.get("search_term", ""),
                "provider": metadata.get("provider", ""),
                "duration": metadata.get("duration", 0),
                "file_name": metadata.get("file_name", ""),
                "file_size": metadata.get("file_size", 0),
            })

        return materials

    except Exception as e:
        logger.error(f"Failed to search materials: {str(e)}")
        return []


def get_all_materials() -> List[Dict]:
    """
    获取所有本地素材

    Returns:
        所有素材列表
    """
    try:
        collection = _get_collection()
        results = collection.get(limit=1000)

        materials = []
        for i, metadata in enumerate(results.get("metadatas", [])):
            # 检查文件是否存在
            video_path = metadata.get("video_path", "")
            if video_path and os.path.exists(video_path):
                materials.append({
                    "id": results["ids"][i],
                    "video_path": video_path,
                    "search_term": metadata.get("search_term", ""),
                    "provider": metadata.get("provider", ""),
                    "duration": metadata.get("duration", 0),
                    "file_name": metadata.get("file_name", ""),
                    "file_size": metadata.get("file_size", 0),
                })

        return materials

    except Exception as e:
        logger.error(f"Failed to get all materials: {str(e)}")
        return []


def get_materials_by_search_term(search_term: str) -> List[Dict]:
    """
    获取指定搜索词的所有素材

    Args:
        search_term: 搜索关键词

    Returns:
        素材列表
    """
    try:
        collection = _get_collection()
        results = collection.get(
            where={"search_term": search_term},
            limit=1000
        )

        materials = []
        for i, metadata in enumerate(results.get("metadatas", [])):
            video_path = metadata.get("video_path", "")
            if video_path and os.path.exists(video_path):
                materials.append({
                    "id": results["ids"][i],
                    "video_path": video_path,
                    "search_term": metadata.get("search_term", ""),
                    "provider": metadata.get("provider", ""),
                    "duration": metadata.get("duration", 0),
                    "file_name": metadata.get("file_name", ""),
                    "file_size": metadata.get("file_size", 0),
                })

        return materials

    except Exception as e:
        logger.error(f"Failed to get materials by search_term: {str(e)}")
        return []


def delete_material(video_id: str) -> bool:
    """
    从素材库删除素材记录（不删除文件）

    Args:
        video_id: 素材 ID

    Returns:
        是否删除成功
    """
    try:
        collection = _get_collection()
        collection.delete(ids=[video_id])
        logger.info(f"Deleted material from library: {video_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete material: {str(e)}")
        return False


def get_material_stats() -> Dict:
    """
    获取素材库统计信息

    Returns:
        统计信息
    """
    try:
        collection = _get_collection()
        results = collection.get(limit=10000)

        stats = {
            "total_count": len(results["ids"]),
            "by_search_term": {},
        }

        for metadata in results.get("metadatas", []):
            term = metadata.get("search_term", "unknown")
            if term not in stats["by_search_term"]:
                stats["by_search_term"][term] = 0
            stats["by_search_term"][term] += 1

        return stats

    except Exception as e:
        logger.error(f"Failed to get material stats: {str(e)}")
        return {"total_count": 0, "by_search_term": {}}


def get_video_paths_for_creation(search_terms: List[str]) -> Dict[str, List[str]]:
    """
    根据搜索词列表获取视频路径，供视频制作使用

    Args:
        search_terms: 搜索词列表

    Returns:
        Dict，key 为 search_term，value 为该词对应的视频路径列表
    """
    result = {}
    for term in search_terms:
        materials = get_materials_by_search_term(term)
        if materials:
            result[term] = [m["video_path"] for m in materials]
    return result


def get_all_video_paths() -> List[str]:
    """
    获取素材库中所有视频的路径

    Returns:
        视频路径列表
    """
    materials = get_all_materials()
    return [m["video_path"] for m in materials if m.get("video_path")]


if __name__ == "__main__":
    # 测试代码
    print("Testing material library...")

    # 添加测试素材
    add_video_material(
        video_path="/test/video1.mp4",
        search_term="自然风景",
        provider="pexels",
        duration=10
    )

    # 搜索测试
    results = search_materials_by_keyword("自然")
    print(f"Search results: {results}")

    # 统计信息
    stats = get_material_stats()
    print(f"Stats: {stats}")
