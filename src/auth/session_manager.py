"""
会话管理器 - 处理用户会话的保存、加载和验证
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from src.config.settings import Settings
from src.utils.logger import get_auth_logger

class SessionManager:
    """会话管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_config = settings.get_auth_config()
        self.logger = get_auth_logger()
        
    def save_session(self, user_id: str, session_data: Dict[str, Any]) -> None:
        """保存用户会话"""
        try:
            # 添加时间戳
            session_data['created_at'] = time.time()
            session_data['expires_at'] = time.time() + self.auth_config.session_timeout
            
            self.settings.save_session(user_id, session_data)
            self.logger.info(f"会话已保存 - 用户: {user_id}")
            
        except Exception as e:
            self.logger.error(f"保存会话失败 - 用户: {user_id}, 错误: {str(e)}")
            raise
    
    def load_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """加载用户会话"""
        try:
            session_data = self.settings.get_decrypted_session(user_id)
            
            if not session_data:
                self.logger.info(f"未找到会话 - 用户: {user_id}")
                return None
            
            # 检查会话是否过期
            if not self.is_session_valid(session_data):
                self.logger.info(f"会话已过期 - 用户: {user_id}")
                self.clear_session(user_id)
                return None
            
            self.logger.info(f"会话加载成功 - 用户: {user_id}")
            return session_data
            
        except Exception as e:
            self.logger.error(f"加载会话失败 - 用户: {user_id}, 错误: {str(e)}")
            return None
    
    def is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """检查会话是否有效"""
        try:
            # 检查必要字段
            required_fields = ['access_token', 'expires_at']
            for field in required_fields:
                if field not in session_data:
                    return False
            
            # 检查是否过期
            current_time = time.time()
            expires_at = session_data.get('expires_at', 0)
            
            if current_time > expires_at:
                return False
            
            # 检查是否需要刷新（还剩30分钟时提前刷新）
            refresh_threshold = expires_at - 1800  # 30分钟
            if current_time > refresh_threshold:
                self.logger.info("会话即将过期，建议刷新")
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查会话有效性失败: {str(e)}")
            return False
    
    def clear_session(self, user_id: str) -> None:
        """清除用户会话"""
        try:
            self.settings.clear_session(user_id)
            self.logger.info(f"会话已清除 - 用户: {user_id}")
            
        except Exception as e:
            self.logger.error(f"清除会话失败 - 用户: {user_id}, 错误: {str(e)}")
    
    def update_session(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """更新会话信息"""
        try:
            session_data = self.load_session(user_id)
            if not session_data:
                return False
            
            # 更新数据
            session_data.update(updates)
            
            # 保存更新后的会话
            self.save_session(user_id, session_data)
            return True
            
        except Exception as e:
            self.logger.error(f"更新会话失败 - 用户: {user_id}, 错误: {str(e)}")
            return False
    
    def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取会话基本信息（不包含敏感数据）"""
        session_data = self.load_session(user_id)
        if not session_data:
            return None
        
        return {
            'user_id': user_id,
            'created_at': datetime.fromtimestamp(session_data.get('created_at', 0)),
            'expires_at': datetime.fromtimestamp(session_data.get('expires_at', 0)),
            'is_valid': self.is_session_valid(session_data),
            'user_info': session_data.get('user_info', {})
        } 