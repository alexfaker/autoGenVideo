"""
常量定义 - 系统中使用的各种常量
"""

class Constants:
    """系统常量总汇"""
    
    # 登录方式常量
    class LoginMethod:
        """登录方式枚举"""
        MANUAL_SMS = "manual_sms"          # 手动输入验证码
        AUTO_SESSION = "auto_session"      # 使用保存的会话
        HYBRID = "hybrid"                  # 混合模式（优先会话，失败时手动）

    # 任务状态常量
    class TaskStatus:
        """任务状态枚举"""
        PENDING = "pending"                # 等待中
        PROCESSING = "processing"          # 处理中
        COMPLETED = "completed"            # 已完成
        FAILED = "failed"                  # 失败
        CANCELLED = "cancelled"            # 已取消
        WAITING_OFF_PEAK = "waiting_off_peak"  # 等待错峰时段

    # HTTP状态码常量
    class HTTPStatus:
        """HTTP状态码"""
        OK = 200
        UNAUTHORIZED = 401
        FORBIDDEN = 403
        NOT_FOUND = 404
        RATE_LIMITED = 429
        INTERNAL_ERROR = 500

    # API端点常量
    class APIEndpoints:
        """Vidu平台API端点"""
        # 基础域名
        BASE_URL = "https://www.vidu.cn"
        API_BASE_URL = "https://service.vidu.cn"
        
        # 认证相关
        SEND_AUTH_CODE = "/iam/v1/users/send-auth-code"
        LOGIN = "/iam/v1/users/login"
        LOGOUT = "/iam/v1/users/logout"
        
        # 用户相关
        USER_INFO = "/iam/v1/users/me"
        USER_PROFILE = "/iam/v1/users/profile"
        
        # 任务相关
        CREATE_TASK = "/vidu/v1/tasks"
        TASK_STATUS = "/vidu/v1/tasks/state"
        TASK_RESULT = "/vidu/v1/tasks/{task_id}/result"
        DOWNLOAD_VIDEO = "/vidu/v1/download/{video_id}"
        TASKS_HISTORY_ME = "/vidu/v1/tasks/history/me"
        
        # 文件上传相关（三步上传流程）
        FILES_UPLOADS_META = "/tools/v1/files/uploads"
        FILES_UPLOADS_FINISH = "/tools/v1/files/uploads/{upload_id}/finish"
        
        # 系统状态
        REGION_INFO = "/vidu/v1/region"
        SYSTEM_STATUS = "/vidu/v1/system/status"

    # 文件处理常量
    class FileConstants:
        """文件处理相关常量"""
        # 支持的图片格式
        SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
        
        # 支持的视频格式
        SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv']
        
        # 文件大小限制（字节）
        MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
        MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
        
        # 图片处理
        MAX_IMAGE_RESOLUTION = (2048, 2048)
        DEFAULT_IMAGE_QUALITY = 85
        
        # 文件MIME类型映射
        CONTENT_TYPE_MAPPING = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }

    # 历史任务查询常量
    class HistoryTasksConfig:
        """历史任务查询配置"""
        # 默认查询参数
        DEFAULT_PAGE_SIZE = 20
        DEFAULT_PAGE = 0
        
        # 支持的任务类型
        TASK_TYPES = [
            "img2video",
            "character2video", 
            "text2video",
            "upscale",
            "extend",
            "headtailimg2video",
            "controlnet",
            "material2video"
        ]
        
        # 默认请求头
        DEFAULT_HEADERS = {
            'accept': '*/*',
            'accept-language': 'zh',
            'origin': 'https://www.vidu.cn',
            'priority': 'u=1, i',
            'referer': 'https://www.vidu.cn/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-app-version': '-',
            'x-platform': 'web'
        }

    # 用户行为模拟常量
    class BehaviorConstants:
        """用户行为模拟常量"""
        # 延时范围（秒）
        MIN_DELAY = 30
        MAX_DELAY = 120
        
        # 打字速度模拟（字符/秒）
        TYPING_SPEED_MIN = 2
        TYPING_SPEED_MAX = 8
        
        # 重试相关
        DEFAULT_RETRY_COUNT = 3
        RETRY_BACKOFF_FACTOR = 2
        
        # 会话超时
        SESSION_CHECK_INTERVAL = 3600  # 1小时
        SESSION_REFRESH_THRESHOLD = 1800  # 30分钟

    # 错峰时段常量
    class OffPeakConstants:
        """错峰时段相关常量"""
        # 默认错峰时段（小时，24小时制）
        DEFAULT_OFF_PEAK_HOURS = [0, 1, 2, 3, 4, 5, 6]
        
        # 检查间隔（秒）
        STATUS_CHECK_INTERVAL = 300  # 5分钟
        
        # 最大等待时间（秒）
        MAX_WAIT_TIME = 3600 * 8  # 8小时

    # 日志常量
    class LogConstants:
        """日志相关常量"""
        # 日志级别
        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"
        
        # 日志格式
        DEFAULT_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
        
        # 日志文件设置
        MAX_LOG_SIZE = "10MB"
        LOG_RETENTION = "30 days"
        LOG_ROTATION = "1 day"

    # 用户提示信息
    class UserPrompts:
        """用户交互提示信息"""
        
        # 登录相关
        SMS_CODE_PROMPT = "请输入收到的手机验证码："
        LOGIN_FAILED = "登录失败，请检查手机号和验证码"
        SESSION_EXPIRED = "会话已过期，需要重新登录"
        
        # 任务相关
        TASK_SUBMITTED = "任务已提交，任务ID: {task_id}"
        WAITING_OFF_PEAK = "当前非错峰时段，任务已排队等待"
        TASK_COMPLETED = "任务完成，正在下载视频..."
        
        # 错误信息
        NETWORK_ERROR = "网络连接错误，请检查网络设置"
        FILE_NOT_FOUND = "文件不存在: {file_path}"
        INVALID_IMAGE_FORMAT = "不支持的图片格式: {format}"
