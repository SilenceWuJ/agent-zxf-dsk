#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志记录模块
提供统一的日志记录功能
"""

import os
import logging
import logging.handlers
from datetime import datetime
from config import DEEPSEEK_API_KEY, ALIYUN_API_KEY


def setup_logger(name='agent-zxf-dsk'):
    """
    设置和配置日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器 - 按天轮转
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 错误日志文件处理器
    error_handler = logging.FileHandler(
        os.path.join(log_dir, 'error.log'),
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


def log_api_call(logger, service_name, endpoint, status, duration=None, error=None):
    """
    记录API调用信息
    
    Args:
        logger: 日志记录器
        service_name: 服务名称（如：DeepSeek、Aliyun、TTS）
        endpoint: API端点
        status: 状态（success, error, timeout）
        duration: 调用时长（秒）
        error: 错误信息
    """
    log_data = {
        'service': service_name,
        'endpoint': endpoint,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    if duration is not None:
        log_data['duration'] = f"{duration:.2f}s"
    
    if error:
        log_data['error'] = str(error)
    
    if status == 'success':
        logger.info(f"API调用成功: {log_data}")
    elif status == 'error':
        logger.error(f"API调用失败: {log_data}")
    elif status == 'timeout':
        logger.warning(f"API调用超时: {log_data}")


def log_user_interaction(logger, user_id, action, details=None):
    """
    记录用户交互信息
    
    Args:
        logger: 日志记录器
        user_id: 用户标识（可以是IP地址或session ID）
        action: 用户行为（如：ask_question, play_audio, etc.）
        details: 详细信息
    """
    log_entry = {
        'user_id': user_id,
        'action': action,
        'timestamp': datetime.now().isoformat()
    }
    
    if details:
        log_entry['details'] = details
    
    logger.info(f"用户交互: {log_entry}")


def log_system_status(logger):
    """
    记录系统状态信息
    
    Args:
        logger: 日志记录器
    """
    status = {
        'timestamp': datetime.now().isoformat(),
        'deepseek_configured': bool(DEEPSEEK_API_KEY),
        'aliyun_configured': bool(ALIYUN_API_KEY),
        'memory_usage': get_memory_usage(),
        'disk_usage': get_disk_usage()
    }
    
    logger.info(f"系统状态: {status}")


def get_memory_usage():
    """获取内存使用情况"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            'total': f"{memory.total / (1024**3):.1f}GB",
            'used': f"{memory.used / (1024**3):.1f}GB",
            'percent': f"{memory.percent}%"
        }
    except ImportError:
        return {'error': 'psutil not installed'}


def get_disk_usage():
    """获取磁盘使用情况"""
    try:
        import psutil
        disk = psutil.disk_usage('.')
        return {
            'total': f"{disk.total / (1024**3):.1f}GB",
            'used': f"{disk.used / (1024**3):.1f}GB",
            'percent': f"{disk.percent}%"
        }
    except ImportError:
        return {'error': 'psutil not installed'}


# 创建全局日志记录器
logger = setup_logger()

def get_logger(name="ai_teacher"):

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # 文件日志
    if not os.path.exists("logs"):
        os.makedirs("logs")

    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger