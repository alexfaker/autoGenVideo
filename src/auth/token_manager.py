"""
Token管理器 - 处理JWT token的本地文件保存和加载
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import get_auth_logger

class TokenManager:
    """JWT Token文件管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.token_file = self.config_dir / ".token"
        self.logger = get_auth_logger()
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_token(self, access_token: str, phone: str, expires_at: Optional[float] = None) -> bool:
        """保存JWT token到本地文件"""
        try:
            # 如果没有提供过期时间，默认24小时后过期
            if expires_at is None:
                expires_at = time.time() + 86400  # 24小时
            
            token_data = {
                'access_token': access_token,
                'expires_at': expires_at,
                'saved_at': time.time(),
                'phone': phone
            }
            
            # 保存到文件
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2)
            
            # 设置文件权限（仅所有者可读写）
            os.chmod(self.token_file, 0o600)
            
            self.logger.info(f"JWT token已保存到文件 - 手机号: {phone}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存token失败: {str(e)}")
            return False
    
    def load_token(self) -> Optional[Dict[str, Any]]:
        """从本地文件加载JWT token"""
        try:
            if not self.token_file.exists():
                self.logger.debug("Token文件不存在")
                return None
            
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 检查token有效性
            if not self.is_token_valid(token_data):
                self.logger.info("Token已过期，清理文件")
                self.clear_token()
                return None
            
            self.logger.info(f"Token加载成功 - 手机号: {token_data.get('phone', '未知')}")
            return token_data
            
        except Exception as e:
            self.logger.error(f"加载token失败: {str(e)}")
            # 如果文件损坏，清理它
            self.clear_token()
            return None
    
    def is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """检查token是否有效"""
        try:
            # 检查必要字段
            required_fields = ['access_token', 'expires_at']
            for field in required_fields:
                if field not in token_data:
                    return False
            
            # 检查是否过期
            current_time = time.time()
            expires_at = token_data.get('expires_at', 0)
            
            if current_time > expires_at:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查token有效性失败: {str(e)}")
            return False
    
    def clear_token(self) -> bool:
        """清除本地token文件"""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                self.logger.info("Token文件已清除")
            return True
            
        except Exception as e:
            self.logger.error(f"清除token文件失败: {str(e)}")
            return False
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """获取token基本信息（不包含敏感数据）"""
        token_data = self.load_token()
        if not token_data:
            return None
        
        from datetime import datetime
        return {
            'phone': token_data.get('phone', '未知'),
            'saved_at': datetime.fromtimestamp(token_data.get('saved_at', 0)),
            'expires_at': datetime.fromtimestamp(token_data.get('expires_at', 0)),
            'is_valid': self.is_token_valid(token_data),
            'file_exists': self.token_file.exists()
        } 