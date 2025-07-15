"""
HTTP请求处理器 - 处理与vidu平台的HTTP通信
"""

import requests
import time
import random
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config.constants import Constants
from src.utils.logger import get_logger

class RequestHandler:
    """HTTP请求处理器"""
    
    def __init__(self, api_base_url: str = "https://service.vidu.cn"):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.logger = get_logger("REQUEST")
        
        # 设置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置默认请求头
        self._setup_default_headers()
    
    def _setup_default_headers(self):
        """设置默认请求头"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发起HTTP请求"""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            self.logger.debug(f"发起请求: {method} {url}")
            
            # 模拟人类行为延时
            self._simulate_human_delay()
            
            response = self.session.request(method, url, timeout=30, **kwargs)
            
            self.logger.debug(f"响应状态: {response.status_code}")
            
            # 处理特殊状态码
            self._handle_response_status(response)
            
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求失败: {str(e)}")
            raise
    
    def _simulate_human_delay(self):
        """模拟人类操作延时"""
        delay = random.uniform(1, 3)  # 1-3秒随机延时
        time.sleep(delay)
    
    def _handle_response_status(self, response: requests.Response):
        """处理响应状态码"""
        if response.status_code == Constants.HTTPStatus.RATE_LIMITED:
            self.logger.warning("触发限流，等待30秒后重试")
            time.sleep(30)
        elif response.status_code == Constants.HTTPStatus.UNAUTHORIZED:
            self.logger.warning("认证失败，需要重新登录")
            # 记录更详细的认证失败信息
            cookie_info = self.get_session_cookies()
            if not cookie_info:
                self.logger.error("未检测到认证cookie，请先登录")
            else:
                self.logger.error(f"认证cookie存在但无效，cookies: {list(cookie_info.keys())}")
            self.logger.info("建议执行: python main.py login <手机号> 重新登录")
        elif response.status_code >= 500:
            self.logger.error(f"服务器错误: {response.status_code}")

        # 对于非2xx状态码，记录响应内容用于调试
        if not 200 <= response.status_code < 300:
            try:
                error_content = response.text[:200] if response.text else "无响应内容"
                self.logger.debug(f"错误响应内容: {error_content}")
            except:
                pass
    
    def set_auth_token(self, token: str):
        """设置认证token (兼容旧方法)"""
        self.set_auth_cookie(token)
    
    def set_auth_cookie(self, token: str):
        """设置认证cookie"""
        # 将token设置为cookie
        self.session.cookies.set('JWT', token, domain='.vidu.cn')
        # 也可以设置其他可能需要的cookie
        self.session.cookies.set('auth_token', token, domain='.vidu.cn')
        self.logger.debug("已设置认证cookie")
    
    def clear_auth_token(self):
        """清除认证token和cookie"""
        # 清除header中的Authorization
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        # 清除认证相关的cookie
        self.session.cookies.clear()
        self.logger.debug("已清除认证token和cookie")

    def get_session_cookies(self) -> Dict[str, str]:
        """获取当前会话的cookie信息"""
        cookies = {}
        for cookie in self.session.cookies:
            cookies[cookie.name] = cookie.value
        return cookies

    def update_headers(self, headers: Dict[str, str]):
        """更新请求头"""
        self.session.headers.update(headers)
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET请求"""
        return self.make_request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST请求"""
        return self.make_request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """PUT请求"""
        return self.make_request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE请求"""
        return self.make_request('DELETE', endpoint, **kwargs) 