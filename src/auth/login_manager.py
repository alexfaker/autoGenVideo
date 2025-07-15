"""
登录管理器 - 处理vidu平台的登录认证，支持手机验证码
"""

import time
import re
from typing import Dict, Any, Optional
from src.config.settings import Settings
from src.config.constants import Constants
from src.auth.session_manager import SessionManager
from src.auth.token_manager import TokenManager
from src.api.request_handler import RequestHandler
from src.utils.logger import get_auth_logger

class LoginManager:
    """登录管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_config = settings.get_auth_config()
        self.vidu_config = settings.get_vidu_config()
        self.session_manager = SessionManager(settings)
        self.token_manager = TokenManager()
        self.request_handler = RequestHandler(self.vidu_config.base_url)
        self.logger = get_auth_logger()
        
    def login(self, phone: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """登录流程主入口"""
        if not account_id:
            account_id = phone
        
        self.logger.info(f"开始登录流程 - 手机号: {phone}")
        
        # 验证手机号格式
        if not self._validate_phone(phone):
            return {
                'success': False,
                'error': '手机号格式不正确',
                'error_code': 'INVALID_PHONE'
            }
        
        try:
            # 根据配置选择登录方式
            if self.auth_config.login_method == Constants.LoginMethod.AUTO_SESSION:
                return self._try_session_login(account_id, phone)
            elif self.auth_config.login_method == Constants.LoginMethod.HYBRID:
                return self._hybrid_login(account_id, phone)
            else:  # MANUAL_SMS
                return self._manual_sms_login(phone, account_id)
                
        except Exception as e:
            self.logger.error(f"登录过程发生异常: {str(e)}")
            return {
                'success': False,
                'error': f'登录异常: {str(e)}',
                'error_code': 'LOGIN_EXCEPTION'
            }
    
    def _validate_phone(self, phone: str) -> bool:
        """验证手机号格式"""
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    def _manual_sms_login(self, phone: str, account_id: str) -> Dict[str, Any]:
        """手机验证码登录 - 真实API版本"""
        self.logger.info("开始手机验证码登录流程")
        
        print(f"\n🔐 Vidu平台登录")
        print(f"📱 手机号: {phone}")

        phone = "+86"+phone
        try:
            # 发送验证码
            print(f"\n📤 正在向 {phone} 发送验证码...")
            send_result = self._send_auth_code(phone)
            if not send_result['success']:
                return send_result
            
            print(f"✅ 验证码已发送")
            
            # 交互式获取验证码
            sms_code = self._get_sms_code_from_user()
            if not sms_code:
                return {
                    'success': False,
                    'error': '用户取消输入验证码',
                    'error_code': 'USER_CANCELLED'
                }
            
            # 验证登录
            print(f"\n🔍 正在验证验证码: {sms_code}")
            login_result = self._verify_login(phone, sms_code)
            if not login_result['success']:
                return login_result
            
            self.logger.info("登录API调用成功")
            
            # 直接使用登录返回的用户信息，无需额外请求
            session_data = {
                'access_token': login_result['access_token'],
                'refresh_token': login_result.get('refresh_token', ''),
                'user_info': login_result.get('user_data', {}),
                'phone': phone,
                'login_time': time.time(),
                'expire_time': login_result.get('expire_time')
            }
            
            # 保存会话（如果启用）
            if self.auth_config.auto_save_session:
                self._save_login_session(account_id, phone, session_data)
            
            print(f"✅ 登录成功！")
            user_info = session_data.get('user_info', {})
            print(f"👤 用户: {user_info.get('nickname', '未知')}")
            print(f"💎 用户ID: {user_info.get('id', '未知')}")
            print(f"📱 手机号: {user_info.get('phone', '未知')}")
            print(f"🎯 订阅计划: {user_info.get('subs_plan', '未知')}")
            print(f"🌍 地区: {user_info.get('region', '未知')}")
            print(f"⏰ token过期时间: {login_result.get('expire_time', '未知')}")
            
            return {
                'success': True,
                'method': 'sms',
                'session_data': session_data,
                'message': '登录成功'
            }
            
        except Exception as e:
            self.logger.error(f"手机验证码登录失败: {str(e)}")
            return {
                'success': False,
                'error': f'登录异常: {str(e)}',
                'error_code': 'SMS_LOGIN_EXCEPTION'
            }
    
    def _send_auth_code(self, phone: str) -> Dict[str, Any]:
        """发送验证码"""
        try:
            # 基于常见API模式，添加必需的channel字段
            payload = {
                'channel': 'sms',
                'receiver': phone,
                'purpose': 'login',
                'locale': 'en'
            }
            
            # 添加必要的请求头
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Origin': 'https://www.vidu.cn',
                'Referer': 'https://www.vidu.cn/login'
            }
            
            response = self.request_handler.post(
                Constants.APIEndpoints.SEND_AUTH_CODE,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                return {'success': True, 'message': '验证码发送成功'}
            else:
                error_msg = f"发送验证码失败，状态码: {response.status_code}"
                
                # 详细调试信息
                self.logger.error(f"Response status: {response.status_code}")
                self.logger.error(f"Response headers: {dict(response.headers)}")
                self.logger.error(f"Response text: {response.text}")
                
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', error_msg)
                        self.logger.error(f"Error data: {error_data}")
                    except Exception as e:
                        self.logger.error(f"Failed to parse JSON: {e}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': f'SEND_CODE_ERROR_{response.status_code}'
                }
                
        except Exception as e:
            error_msg = f"发送验证码异常: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': 'SEND_CODE_EXCEPTION'
            }
    
    def _verify_login(self, phone: str, auth_code: str) -> Dict[str, Any]:
        """验证登录"""
        try:
            # {"id_type":"phone","identity":"+8617701058047","auth_type":"authcode","credential":"620363","device_id":"DEVICE_c2d3ac2e-a61c-421d-b126-1a818b6f27fa","invite_code":"","receive_marketing_msg":false}
            payload = {
                'id_type': 'phone',
                'identity': phone,
                'auth_type': 'authcode',
                'credential': auth_code,
                'device_id': 'DEVICE_c2d3ac2e-a61c-421d-b126-1a818b6f27fa',
                'invite_code': '',
                'receive_marketing_msg': False
            }
            
            # 添加必要的请求头
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Origin': 'https://www.vidu.cn',
                'Referer': 'https://www.vidu.cn/login'
            }
            
            response = self.request_handler.post(
                Constants.APIEndpoints.LOGIN,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                login_data = response.json()
                
                # 提取token并设置到cookie中
                token = login_data.get('token')
                if token:
                    # 设置cookie到请求处理器
                    self.request_handler.set_auth_cookie(token)
                    
                    # 保存token到本地文件
                    expire_time = login_data.get('expire_time')
                    expires_at = None
                    if expire_time:
                        # 如果有过期时间，转换为时间戳
                        try:
                            if isinstance(expire_time, str):
                                from datetime import datetime
                                expires_at = datetime.fromisoformat(expire_time.replace('Z', '+00:00')).timestamp()
                            elif isinstance(expire_time, (int, float)):
                                expires_at = expire_time
                        except:
                            pass
                    
                    # 从phone参数中提取手机号（移除+86前缀）
                    clean_phone = phone.replace('+86', '') if phone.startswith('+86') else phone
                    self.token_manager.save_token(token, clean_phone, expires_at)
                
                return {
                    'success': True,
                    'access_token': token,
                    'refresh_token': login_data.get('refresh_token', ''),
                    'user_data': login_data.get('user', {}),
                    'expire_time': login_data.get('expire_time')
                }
            else:
                error_msg = f"登录验证失败，状态码: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', error_msg)
                    except:
                        pass
                
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': f'LOGIN_ERROR_{response.status_code}'
                }
                
        except Exception as e:
            error_msg = f"登录验证异常: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': 'LOGIN_EXCEPTION'
            }
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """获取用户信息 (备用方法，登录时已返回完整用户信息)"""
        try:
            # 使用cookie认证而不是Bearer token
            self.request_handler.set_auth_cookie(access_token)
            
            response = self.request_handler.get(
                Constants.APIEndpoints.USER_INFO
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'success': True,
                    'user_info': user_data
                }
            else:
                self.logger.warning(f"获取用户信息失败，状态码: {response.status_code}")
                return {
                    'success': False,
                    'user_info': {}
                }
                
        except Exception as e:
            self.logger.warning(f"获取用户信息异常: {str(e)}")
            return {
                'success': False,
                'user_info': {}
            }
    
    def _get_sms_code_from_user(self) -> Optional[str]:
        """交互式获取用户输入的验证码"""
        if not self.auth_config.interactive_login:
            self.logger.error("交互式登录已禁用，无法获取验证码")
            return None
        
        try:
            print(f"\n{Constants.UserPrompts.SMS_CODE_PROMPT}")
            print("🚪 输入 'q' 或 'quit' 可以取消登录")
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    sms_code = input("🔢 验证码: ").strip()
                    
                    if sms_code.lower() in ['q', 'quit']:
                        self.logger.info("用户取消登录")
                        return None
                    
                    # 验证验证码格式
                    if len(sms_code) == 6 and sms_code.isdigit():
                        return sms_code
                    else:
                        print(f"❌ 验证码格式不正确，应为6位数字 (剩余尝试次数: {max_attempts - attempt - 1})")
                        if attempt == max_attempts - 1:
                            print("❌ 尝试次数已用完")
                            return None
                        continue
                        
                except KeyboardInterrupt:
                    print("\n\n❌ 用户中断登录")
                    return None
                    
            return None
                
        except Exception as e:
            self.logger.error(f"获取验证码输入失败: {str(e)}")
            return None
    
    def _save_login_session(self, account_id: str, phone: str, session_data: Dict[str, Any]):
        """保存登录会话"""
        try:
            self.session_manager.save_session(account_id, session_data)
            
            # 同时保存账号信息
            account_info = {
                'phone': phone,
                'last_login': time.time(),
                'login_method': 'sms'
            }
            self.settings.save_encrypted_account(account_id, account_info)
            
            self.logger.info(f"会话和账号信息已保存 - 账号: {account_id}")
            print(f"💾 会话信息已保存，下次可直接使用")
            
        except Exception as e:
            self.logger.error(f"保存会话失败: {str(e)}")
    
    def _try_session_login(self, account_id: str, phone: str) -> Dict[str, Any]:
        """尝试使用保存的会话登录"""
        self.logger.info("尝试使用保存的会话登录")
        
        session_data = self.session_manager.load_session(account_id)
        if session_data and self.session_manager.is_session_valid(session_data):
            print(f"✅ 找到有效会话，自动登录成功")
            print(f"👤 用户: {session_data.get('user_info', {}).get('nickname', '未知')}")
            return {
                'success': True,
                'method': 'session',
                'session_data': session_data,
                'message': '会话登录成功'
            }
        
        # 会话无效，清除并返回失败
        self.session_manager.clear_session(account_id)
        return {
            'success': False,
            'error': '会话已失效',
            'error_code': 'SESSION_INVALID'
        }
    
    def _hybrid_login(self, account_id: str, phone: str) -> Dict[str, Any]:
        """混合登录模式：优先会话，失败时手动验证码"""
        # 先尝试会话登录
        session_result = self._try_session_login(account_id, phone)
        if session_result['success']:
            return session_result
        
        print(f"💡 未找到有效会话，切换到手机验证码登录")
        return self._manual_sms_login(phone, account_id)

    def try_token_login(self, phone: str = None) -> Dict[str, Any]:
        """尝试使用本地token文件自动登录"""
        self.logger.info("尝试使用本地token文件自动登录")
        
        token_data = self.token_manager.load_token()
        if not token_data:
            return {
                'success': False,
                'error': '未找到有效的token文件',
                'error_code': 'NO_TOKEN_FILE'
            }
        
        access_token = token_data.get('access_token')
        token_phone = token_data.get('phone')
        
        # 如果指定了手机号，检查是否匹配
        if phone and phone != token_phone:
            self.logger.info(f"Token文件手机号({token_phone})与指定手机号({phone})不匹配")
            return {
                'success': False,
                'error': 'Token文件与指定手机号不匹配',
                'error_code': 'PHONE_MISMATCH'
            }
        
        if access_token:
            # 设置认证信息到请求处理器
            self.request_handler.set_auth_cookie(access_token)
            
            # 尝试验证token是否仍然有效（通过API调用）
            try:
                response = self.request_handler.get(Constants.APIEndpoints.USER_INFO)
                if response.status_code == 200:
                    user_data = response.json()
                    
                    print(f"✅ Token自动登录成功")
                    print(f"📱 手机号: {token_phone}")
                    print(f"👤 用户: {user_data.get('nickname', '未知')}")
                    
                    # 构建session数据
                    session_data = {
                        'access_token': access_token,
                        'user_info': user_data,
                        'phone': token_phone,
                        'login_time': time.time(),
                        'method': 'token_auto'
                    }
                    
                    return {
                        'success': True,
                        'method': 'token',
                        'session_data': session_data,
                        'message': 'Token自动登录成功'
                    }
                else:
                    # Token无效，清理文件
                    self.logger.info("Token验证失败，清理本地文件")
                    self.token_manager.clear_token()
                    return {
                        'success': False,
                        'error': 'Token已失效',
                        'error_code': 'TOKEN_INVALID'
                    }
            except Exception as e:
                self.logger.error(f"Token验证异常: {str(e)}")
                return {
                    'success': False,
                    'error': f'Token验证异常: {str(e)}',
                    'error_code': 'TOKEN_VERIFY_ERROR'
                }
        
        return {
            'success': False,
            'error': 'Token文件中未找到access_token',
            'error_code': 'NO_ACCESS_TOKEN'
        }

    def logout(self, account_id: str) -> bool:
        """登出"""
        try:
            # 清除本地会话
            self.session_manager.clear_session(account_id)
            
            # 清除token文件
            self.token_manager.clear_token()
            
            # 清除请求器的认证token
            self.request_handler.clear_auth_token()
            
            self.logger.info(f"登出成功 - 账号: {account_id}")
            print(f"👋 登出成功")
            return True
            
        except Exception as e:
            self.logger.error(f"登出失败: {str(e)}")
            return False 