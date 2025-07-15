"""
日志系统 - 统一的日志管理
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional
from src.config.constants import Constants

class Logger:
    """统一日志管理器"""
    
    def __init__(self, log_dir: str = "data/logs", app_name: str = "autoGenVideo"):
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 移除默认处理器
        logger.remove()
        
        # 设置日志配置
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志配置"""
        
        # 控制台输出 - 只显示INFO及以上级别
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
            level="INFO",
            colorize=True
        )
        
        # 详细日志文件 - 记录所有级别
        logger.add(
            self.log_dir / f"{self.app_name}.log",
            format=Constants.LogConstants.DEFAULT_FORMAT,
            level="DEBUG",
            rotation=Constants.LogConstants.LOG_ROTATION,
            retention=Constants.LogConstants.LOG_RETENTION,
            compression="zip",
            encoding="utf-8"
        )
        
        # 错误日志文件 - 只记录ERROR及以上级别
        logger.add(
            self.log_dir / f"{self.app_name}_error.log",
            format=Constants.LogConstants.DEFAULT_FORMAT,
            level="ERROR",
            rotation=Constants.LogConstants.LOG_ROTATION,
            retention=Constants.LogConstants.LOG_RETENTION,
            compression="zip",
            encoding="utf-8"
        )
        
        # 登录相关日志 - 单独记录
        logger.add(
            self.log_dir / "auth.log",
            format=Constants.LogConstants.DEFAULT_FORMAT,
            level="INFO",
            rotation="1 day",
            retention="7 days",
            filter=lambda record: "auth" in record["extra"],
            encoding="utf-8"
        )
    
    def get_logger(self, name: Optional[str] = None):
        """获取logger实例"""
        if name:
            return logger.bind(name=name)
        return logger
    
    def get_auth_logger(self):
        """获取认证专用logger"""
        return logger.bind(auth=True, name="AUTH")

# 全局logger实例
_logger_instance = None

def get_logger(name: Optional[str] = None):
    """获取全局logger实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance.get_logger(name)

def get_auth_logger():
    """获取认证专用logger"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance.get_auth_logger() 