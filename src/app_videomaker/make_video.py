"""
视频制作脚本
直接调用 src/app/services 中的服务来制作视频，无需通过 FastAPI 接口
"""
import os
import sys
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlmodel import select

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from loguru import logger
from src.db.session import get_db_context
from src.models.models import VideoTask
from services import task as task_service
from utils import utils
from utils import minio_utils

# 线程池大小
MAX_WORKERS = 10
# 轮询间隔（秒）
POLL_INTERVAL = 60
# 每次最多获取的任务数
MAX_TASKS_PER_POLL = 10


def make_video(
    **params
) -> dict:
    """
    制作视频
    
    Args:
        video_subject: 视频主题
        video_script: 视频脚本（如果为空，则使用 AI 生成）
        video_language: 视频语言
        voice_name: 语音名称
        video_aspect: 视频比例 (portrait/landscape)
        video_count: 生成视频数量
        video_clip_duration: 每个视频片段的时长（秒）
        subtitle_enabled: 是否启用字幕
        font_name: 字体名称
        font_size: 字体大小
        text_fore_color: 文字前景色
        stroke_color: 描边颜色
        bgm_type: 背景音乐类型
        bgm_volume: 背景音乐音量
        voice_volume: 语音音量
        voice_rate: 语速
        video_source: 视频来源 (pexels/pixabay/local)
        video_materials: 本地视频素材列表
        n_threads: 并行线程数
        
    Returns:
        包含生成的视频路径的字典
    """
    
    # 生成任务 ID
    task_id = utils.get_uuid()
    
    # 从 params 中获取视频主题
    video_subject = params.get('video_subject', '未命名')
    logger.info(f"开始制作视频，任务 ID: {task_id}")
    logger.info(f"视频主题：{video_subject}")
    
    
    
    # 执行视频制作任务
    result = task_service.start(task_id=task_id, dict_params=params)
    
    if result and "videos" in result:
        logger.success(f"视频制作完成！")
        for i, video_path in enumerate(result["videos"], 1):
            logger.success(f"  视频 {i}: {video_path}")
        return result
    else:
        logger.error("视频制作失败")
        return None


def execute_task(db_task_id: int):
    """
    执行单个视频任务
    """
    logger.info(f"开始执行任务: {db_task_id}")
    
    # 获取任务信息并尝试修改状态为进行中（双重检查）
    with get_db_context() as session:
        task = session.get(VideoTask, db_task_id)
        if not task:
            logger.error(f"任务不存在: {db_task_id}")
            return
        
        # 双重检查：确保任务状态仍然是待处理（防止重复执行）
        if task.status != 0:
            logger.warning(f"任务状态已变更，跳过执行: {db_task_id}, 当前状态: {task.status}")
            return
        # 修改状态为进行中
        task.status = 1  # 1-进行中
        #task.updated_at = utils.get_current_time()
        session.commit()
        session.refresh(task)
        
        # 解析配置
        try:
            config_data = json.loads(task.config_json)
            params = config_data.get("params", {})
            params['video_script'] = config_data.get('script', '')
            params['video_terms'] = config_data.get('search_terms', '')
        except json.JSONDecodeError:
            logger.error(f"任务配置解析失败: {db_task_id}")
            task.status = -1  # -1-失败
            task.result_message = "配置解析失败"
            session.commit()
            return
    
    # 执行视频制作
    try:
        result = make_video(
            **params
        )
        
        # 更新任务状态
        with get_db_context() as session:
            task = session.get(VideoTask, db_task_id)
            if task:
                if result and "videos" in result:
                    # 任务成功完成
                    task.status = 2  # 2-成功
                    # task.output_file = ",".join(result["videos"])
                    task.result_message = f"成功生成 {len(result['videos'])} 个视频"
                    
                    # 上传视频到 MinIO 并更新下载链接
                    try:
                        minio_utils.batch_upload_videos(db_task_id, result["videos"])
                    except Exception as upload_error:
                        logger.warning(f"上传视频到 MinIO 失败: {upload_error}")
                else:
                    # 任务失败
                    task.status = -1  # -1-失败
                    task.result_message = "视频生成失败"
                #task.updated_at = utils.get_current_time()
                session.commit()
                logger.info(f"任务 {db_task_id} 完成，状态: {task.status}")
    
    except Exception as e:
        logger.error(f"任务 {db_task_id} 执行异常: {str(e)}")
        # 更新任务状态为失败
        with get_db_context() as session:
            task = session.get(VideoTask, db_task_id)
            if task:
                task.status = -1  # -1-失败
                task.result_message = f"执行异常: {str(e)}"
                #task.updated_at = utils.get_current_time()
                session.commit()


def get_pending_tasks(limit: int = 10) -> list:
    """
    查询数据库中待处理的任务
    """
    try:
        with get_db_context() as session:
            statement = select(VideoTask).where(VideoTask.status == 0).limit(limit)
            tasks = session.exec(statement).all()
            return [task.id for task in tasks]
    except Exception as e:
        logger.error(f"查询待处理任务失败: {str(e)}")
        return []


def main():
    """
    主循环：定时查询任务并执行
    """
    logger.info("=" * 60)
    logger.info("MoneyPrinter 视频任务调度器")
    logger.info("=" * 60)
    
    # 创建线程池
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        logger.info(f"创建线程池，大小: {MAX_WORKERS}")
        
        # 用于跟踪正在运行的任务
        futures = set()
        
        try:
            while True:
                # 清理已完成的任务
                completed_futures = {f for f in futures if f.done()}
                for f in completed_futures:
                    futures.remove(f)
                
                # 查询待处理任务
                pending_tasks = get_pending_tasks(MAX_TASKS_PER_POLL)
                logger.info(f"查询到 {len(pending_tasks)} 个待处理任务")
                
                # 计算线程池剩余容量
                current_running = len(futures)
                available_slots = MAX_WORKERS - current_running
                logger.info(f"当前运行任务数: {current_running}, 可用槽位: {available_slots}")
                
                if pending_tasks and available_slots > 0:
                    # 如果线程池不满，提交新任务
                    tasks_to_submit = min(len(pending_tasks), available_slots)
                    logger.info(f"将提交 {tasks_to_submit} 个任务")
                    
                    for task_id in pending_tasks[:tasks_to_submit]:
                        try:
                            # 提交任务到线程池
                            future = executor.submit(execute_task, task_id)
                            futures.add(future)
                            logger.info(f"提交任务到线程池: {task_id}")
                        except Exception as e:
                            logger.error(f"提交任务失败 {task_id}: {str(e)}")
                elif available_slots == 0:
                    logger.info("线程池已满，等待任务完成")
                
                # 等待下次轮询
                logger.info(f"等待 {POLL_INTERVAL} 秒后再次查询...")
                time.sleep(POLL_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭线程池...")
            # 取消所有未完成的任务
            for future in futures:
                future.cancel()
            logger.info("线程池已关闭")


if __name__ == "__main__":
    # 配置日志格式
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    
    # 启动任务调度器
    main()
