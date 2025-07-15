"""
配置管理系统 - 处理所有配置文件的读取、验证和管理
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from cryptography.fernet import Fernet

@dataclass
class ViduConfig:
    """Vidu平台相关配置"""
    base_url: str
    api_version: str
    off_peak_hours: list
    max_retry_count: int
    request_timeout: int
    max_concurrent_tasks: int

@dataclass
class AuthConfig:
    """认证相关配置 - 支持手机验证码登录"""
    login_method: str  # "manual_sms", "auto_session", "hybrid"
    session_persistence: bool
    max_login_attempts: int
    sms_timeout: int  # 验证码等待超时时间
    interactive_login: bool  # 是否允许交互式登录
    auto_save_session: bool  # 是否自动保存会话
    session_timeout: int  # 会话超时时间（秒）

@dataclass
class BehaviorConfig:
    """用户行为模拟配置"""
    min_delay: int
    max_delay: int
    use_proxy: bool
    simulate_typing_speed: bool
    user_agents_file: str

class Settings:
    """配置管理主类"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self.accounts_file = self.config_dir / "accounts.json"
        self.session_file = self.config_dir / "sessions.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._config_data = self._load_config()
        self._encryption_key = self._get_or_create_encryption_key()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载主配置文件"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_or_create_encryption_key(self) -> Fernet:
        """获取或创建加密密钥"""
        key_file = self.config_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限（仅所有者可读写）
            os.chmod(key_file, 0o600)
            
        return Fernet(key)
    
    def get_vidu_config(self) -> ViduConfig:
        """获取Vidu平台配置"""
        vidu_cfg = self._config_data.get('vidu', {})
        return ViduConfig(
            base_url=vidu_cfg.get('base_url', 'https://www.vidu.cn'),
            api_version=vidu_cfg.get('api_version', 'v1'),
            off_peak_hours=vidu_cfg.get('off_peak_hours', [0, 1, 2, 3, 4, 5, 6]),
            max_retry_count=vidu_cfg.get('max_retry_count', 3),
            request_timeout=vidu_cfg.get('request_timeout', 30),
            max_concurrent_tasks=vidu_cfg.get('max_concurrent_tasks', 5)
        )
    
    def get_auth_config(self) -> AuthConfig:
        """获取认证配置 - 支持手机验证码"""
        auth_cfg = self._config_data.get('authentication', {})
        return AuthConfig(
            login_method=auth_cfg.get('login_method', 'manual_sms'),
            session_persistence=auth_cfg.get('session_persistence', True),
            max_login_attempts=auth_cfg.get('max_login_attempts', 3),
            sms_timeout=auth_cfg.get('sms_timeout', 300),  # 5分钟
            interactive_login=auth_cfg.get('interactive_login', True),
            auto_save_session=auth_cfg.get('auto_save_session', True),
            session_timeout=auth_cfg.get('session_timeout', 3600) # 1小时
        )
    
    def get_behavior_config(self) -> BehaviorConfig:
        """获取用户行为模拟配置"""
        behavior_cfg = self._config_data.get('behavior', {})
        return BehaviorConfig(
            min_delay=behavior_cfg.get('min_delay', 30),
            max_delay=behavior_cfg.get('max_delay', 120),
            use_proxy=behavior_cfg.get('use_proxy', False),
            simulate_typing_speed=behavior_cfg.get('simulate_typing_speed', True),
            user_agents_file=behavior_cfg.get('user_agents_file', 'config/user_agents.txt')
        )
    
    def save_encrypted_account(self, account_id: str, account_data: Dict[str, Any]) -> None:
        """保存加密的账号信息"""
        accounts = self.load_accounts()
        
        # 加密敏感信息
        if 'phone' in account_data:
            account_data['phone'] = self._encryption_key.encrypt(
                account_data['phone'].encode()
            ).decode()
        
        accounts[account_id] = account_data
        
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
        
        # 设置文件权限
        os.chmod(self.accounts_file, 0o600)
    
    def load_accounts(self) -> Dict[str, Any]:
        """加载账号信息"""
        if not self.accounts_file.exists():
            return {}
            
        with open(self.accounts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_decrypted_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取解密的账号信息"""
        accounts = self.load_accounts()
        account = accounts.get(account_id)
        
        if not account:
            return None
        
        # 解密敏感信息
        if 'phone' in account and isinstance(account['phone'], str):
            try:
                account['phone'] = self._encryption_key.decrypt(
                    account['phone'].encode()
                ).decode()
            except Exception:
                # 如果解密失败，可能是未加密的数据
                pass
        
        return account
    
    def save_session(self, account_id: str, session_data: Dict[str, Any]) -> None:
        """保存会话信息"""
        sessions = self.load_sessions()
        
        # 加密会话数据
        encrypted_session = {}
        for key, value in session_data.items():
            if isinstance(value, str):
                encrypted_session[key] = self._encryption_key.encrypt(
                    value.encode()
                ).decode()
            else:
                encrypted_session[key] = value
        
        sessions[account_id] = encrypted_session
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=2)
        
        # 设置文件权限
        os.chmod(self.session_file, 0o600)
    
    def load_sessions(self) -> Dict[str, Any]:
        """加载会话信息"""
        if not self.session_file.exists():
            return {}
            
        with open(self.session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_decrypted_session(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取解密的会话信息"""
        sessions = self.load_sessions()
        session = sessions.get(account_id)
        
        if not session:
            return None
        
        # 解密会话数据
        decrypted_session = {}
        for key, value in session.items():
            if isinstance(value, str):
                try:
                    decrypted_session[key] = self._encryption_key.decrypt(
                        value.encode()
                    ).decode()
                except Exception:
                    decrypted_session[key] = value
            else:
                decrypted_session[key] = value
        
        return decrypted_session
    
    def clear_session(self, account_id: str) -> None:
        """清除指定账号的会话"""
        sessions = self.load_sessions()
        if account_id in sessions:
            del sessions[account_id]
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2)
    
    def get_storage_paths(self) -> Dict[str, Path]:
        """获取存储路径配置"""
        storage_cfg = self._config_data.get('storage', {})
        base_paths = {
            'input': Path(storage_cfg.get('input_dir', 'data/input_images')),
            'output': Path(storage_cfg.get('output_dir', 'data/output_videos')),
            'logs': Path(storage_cfg.get('log_dir', 'data/logs')),
            'cache': Path(storage_cfg.get('cache_dir', 'data/cache'))
        }
        
        # 确保目录存在
        for path in base_paths.values():
            path.mkdir(parents=True, exist_ok=True)
        
        return base_paths 