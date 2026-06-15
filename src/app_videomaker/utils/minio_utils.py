"""
MinIO 存储工具
用于上传视频文件到 MinIO 并获取下载链接
"""
import os
from datetime import datetime
from typing import Optional
import re
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path
import sys
# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))
def load_minio_config() -> dict:
    """从环境变量加载 MinIO 配置"""
    load_dotenv()
    d =  {
        "enabled": os.getenv("MINIO_ENABLED", "false").lower() == "true",
        "endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        "access_key": os.getenv("MINIO_ACCESS_KEY", ""),
        "secret_key": os.getenv("MINIO_SECRET_KEY", ""),
        "bucket": os.getenv("MINIO_BUCKET", "videos"),
        "secure": os.getenv("MINIO_SECURE", "false").lower() == "true",
    }
    return d


def get_presigned_url(client, bucket_name: str, object_name: str, expires: int = 3600) -> str:
    """
    获取预签名下载 URL
    
    Args:
        client: MinIO 客户端实例
        bucket_name: 存储桶名称
        object_name: 对象名称
        expires: URL 过期时间（秒），默认 1 小时
        
    Returns:
        预签名下载 URL
    """
    from datetime import timedelta
    try:
        url = client.presigned_get_object(bucket_name, object_name, expires=timedelta(seconds=expires))
        return url
    except Exception as e:
        logger.error(f"获取预签名 URL 失败: {e}")
        raise


def upload_file_to_minio(
    file_path: str,
    object_name: Optional[str] = None,
    bucket_name: Optional[str] = None,
    content_type: str = "video/mp4",
) -> Optional[str]:
    """
    上传文件到 MinIO
    
    Args:
        file_path: 本地文件路径
        object_name: MinIO 中的对象名称（若不指定则自动生成）
        bucket_name: 存储桶名称（若不指定则使用配置中的默认桶）
        content_type: 文件的 Content-Type
        
    Returns:
        预签名下载 URL，失败返回 None
    """
    config = load_minio_config()
    
    if not config.get("enabled"):
        logger.warning("MinIO 未启用，跳过上传")
        return None
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
    
    try:
        from minio import Minio
        
        # 构建 MinIO 客户端
        client = Minio(
            config["endpoint"],
            access_key=config["access_key"],
            secret_key=config["secret_key"],
            secure=config["secure"],
        )
        
        # 使用默认桶或指定的桶
        bucket = bucket_name or config["bucket"]
        
        # 确保存储桶存在
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"创建存储桶: {bucket}")
        
        # 生成对象名称
        if object_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = os.path.splitext(file_path)[1]
            object_name = f"videos/{timestamp}{file_ext}"
        
        # 上传文件
        file_size = os.path.getsize(file_path)
        client.put_object(
            bucket,
            object_name,
            open(file_path, "rb"),
            file_size,
            content_type=content_type,
        )
        logger.info(f"文件上传成功: {file_path} -> {bucket}/{object_name}")
        
        # 获取预签名下载 URL
        download_url = get_presigned_url(client, bucket, object_name)
        return download_url
        
    except ImportError:
        logger.error("MinIO SDK 未安装，请运行: pip install minio")
        return None
    except Exception as e:
        logger.error(f"上传文件到 MinIO 失败: {e}")
        return None


def upload_video_and_update_task(
    task_id: int,
    video_path: str,
    bucket_name: Optional[str] = None,
) -> Optional[str]:
    """
    上传视频到 MinIO 并更新任务表的下载链接
    
    Args:
        task_id: 视频任务 ID
        video_path: 视频文件路径
        bucket_name: 存储桶名称
        
    Returns:
        下载 URL，失败返回 None
    """
    config = load_minio_config()
    
    if not config.get("enabled"):
        logger.warning("MinIO 未启用，跳过上传")
        return None
    
    # 上传文件到 MinIO
    download_url = upload_file_to_minio(
        file_path=video_path,
        bucket_name=bucket_name,
    )
    
    if download_url is None:
        return None
    
    # 更新数据库中的视频 URL
    try:
        from src.db.session import get_db_context
        from src.models.models import VideoTask
        
        with get_db_context() as session:
            task = session.get(VideoTask, task_id)
            if task:
                
                task.output_file = download_url
                
                
                session.commit()
                logger.info(f"任务 {task_id} 的视频链接已更新: {download_url}")
            else:
                logger.warning(f"任务 {task_id} 不存在")
                
    except Exception as e:
        logger.error(f"更新任务视频链接失败: {e}")
    
    return download_url


def batch_upload_videos(
    task_id: int,
    video_paths: list,
    bucket_name: Optional[str] = None,
) -> list:
    """
    批量上传视频到 MinIO
    
    Args:
        task_id: 视频任务 ID
        video_paths: 视频文件路径列表
        bucket_name: 存储桶名称
        
    Returns:
        下载 URL 列表
    """
    urls = []
    for video_path in video_paths:
        url = upload_video_and_update_task(task_id, video_path, bucket_name)
        if url:
            urls.append(url)
    return urls
if __name__ == '__main__':
    # Test load_minio_config
    # print("Testing load_minio_config...")
    # config = load_minio_config()
    # print(f"Config: {config}")
    
    # Test upload_file_to_minio with a test file
    print("\nTesting upload_file_to_minio...")
    
    # Create a test file
    test_file_path = r"D:\workspace\MoneyPrinter-by-NiceGUI\src\storage\tasks\967ee16f-0b4c-49eb-8980-a349d751cca4\final-1.mp4"
    
    
    try:
        urls = batch_upload_videos(
            task_id=3,
            video_paths=[test_file_path],
        )
        if urls:
            print(f"Upload successful, URL: {urls}")
        else:
            print("Upload returned None (MinIO might be disabled or failed)")
    except Exception as e:
        print(f"Upload failed with exception: {e}")
    finally:
        pass
        # Clean up test file
        # if os.path.exists(test_file_path):
        #     os.remove(test_file_path)
        #     print(f"Cleaned up test file: {test_file_path}")
    
    print("\nTests completed.")
