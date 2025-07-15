<!--
 * @Author: alexfaker
 * @Date: 2025-07-11 22:12:12
 * @LastEditors: alexfaker 1396657985@qq.com
 * @LastEditTime: 2025-07-11 22:26:45
 * @FilePath: /autoGenVideo/task_autogen_video.md
 * @Description: 
 * 
 * Copyright (c) 2025 by ${git_name}, All Rights Reserved. 
-->
# 上下文
文件名：task_autogen_video.md
创建于：2024-12-20
创建者：AI Assistant
关联协议：RIPER-5 + Multidimensional + Agent Protocol

# 任务描述
为vidu.cn平台开发一套自动化工具，实现图生视频任务的自动提交和结果下载：

1. 使用错峰模式提交图生视频任务（无积分消耗）
2. 模拟用户行为，避免被识别为脚本
3. 支持自动登录、任务提交、状态检查、结果下载
4. 基于HTTP API调用而非浏览器自动化
5. 添加随机延时（30-120秒）和反反爬机制
6. 定时检测昨日任务状态并下载结果
7. 使用Python实现

# 项目概述
autoGenVideo是一个针对vidu.cn平台的自动化图生视频工具，旨在利用错峰模式实现零成本视频生成。项目需要解决：

- API接口逆向工程
- 用户认证和会话管理
- 任务状态追踪和管理
- 文件上传和下载
- 反反爬和用户行为模拟
- 定时任务调度

---
*以下部分由 AI 在协议执行过程中维护*
---

# 分析 (由 RESEARCH 模式填充)

## 当前项目状态
- 空项目，仅包含基础的LICENSE和README.md文件
- 需要从零开始构建完整的自动化框架

## 技术栈需求分析
- Python作为主要开发语言
- HTTP请求库（requests）用于API调用
- 文件处理和存储管理
- 定时任务调度（APScheduler或crontab）
- 配置管理（JSON/YAML）
- 日志记录和错误处理

## 关键研究发现
- 搜索结果显示存在vidu.com平台（可能是用户提到的vidu.cn的正确域名）
- vidu.com确实具有"Off-Peak Mode"（错峰模式）功能
- 该平台是基于AI的视频生成服务，支持文生视频和图生视频
- 从搜索结果看，vidu.com使用Stripe进行支付处理
- 平台具有不同的订阅计划（Free, Standard, Premium, Ultimate）

## 平台特征分析
1. **Off-Peak Mode机制**: 确实存在错峰模式，可能在特定时间段免费使用
2. **API接口**: 从搜索到的GitHub项目可以看出存在API文档
3. **反反爬需求**: 需要模拟用户行为，避免被识别为自动化脚本
4. **身份验证**: 需要账号登录和会话管理
5. **任务异步处理**: 视频生成可能需要较长时间，需要轮询检查状态 

# 提议的解决方案 (由 INNOVATE 模式填充)

## 选定技术方案
经过多方案对比分析，决定采用**纯HTTP API逆向工程方案**，主要理由：

1. **部署兼容性**: 完全符合无浏览器服务器环境要求
2. **性能优势**: 轻量级实现，资源消耗最小
3. **可控性强**: 精确控制请求行为，更好地实现反反爬策略
4. **可扩展性**: 易于添加多账号支持和任务队列管理

## 核心技术策略
1. **渐进式逆向**: 先实现基础功能，再逐步完善高级特性
2. **行为模拟**: 基于真实用户行为模式设计请求序列
3. **容错设计**: 多层次的错误处理和重试机制
4. **模块化架构**: 独立的功能模块便于维护和扩展

# 实施计划 (由 PLAN 模式生成)

## 项目架构设计

### 目录结构
```
autoGenVideo/
├── src/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── login_manager.py      # 登录和认证管理
│   │   └── session_manager.py    # 会话状态管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── vidu_client.py        # vidu.com API客户端
│   │   ├── request_handler.py    # HTTP请求处理
│   │   └── endpoints.py          # API端点定义
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── task_manager.py       # 任务管理器
│   │   ├── scheduler.py          # 任务调度器
│   │   └── status_checker.py     # 状态检查器
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_manager.py       # 文件上传下载
│   │   ├── behavior_simulator.py # 用户行为模拟
│   │   ├── anti_detection.py     # 反反爬策略
│   │   └── logger.py             # 日志系统
│   └── config/
│       ├── __init__.py
│       ├── settings.py           # 配置管理
│       └── constants.py          # 常量定义
├── config/
│   ├── config.json              # 主配置文件
│   ├── accounts.json            # 账号信息（加密存储）
│   └── task_templates.json      # 任务模板
├── data/
│   ├── input_images/            # 输入图片目录
│   ├── output_videos/           # 输出视频目录
│   ├── logs/                    # 日志文件
│   └── cache/                   # 缓存数据
├── scripts/
│   ├── submit_task.py           # 任务提交脚本
│   ├── check_results.py         # 结果检查脚本
│   └── daily_checker.py         # 每日定时检查脚本
├── requirements.txt             # 依赖包列表
├── setup.py                     # 安装配置
├── README.md                    # 项目说明
└── main.py                      # 主程序入口
```

## 核心模块详细设计

### 1. 认证模块 (src/auth/)

**login_manager.py**
```python
class LoginManager:
    def __init__(self, config: Dict[str, Any])
    def login(self, username: str, password: str) -> Dict[str, str]
    def refresh_token(self, refresh_token: str) -> Dict[str, str]
    def logout(self) -> bool
    def get_user_info(self) -> Dict[str, Any]
```

**session_manager.py**
```python
class SessionManager:
    def __init__(self, storage_path: str)
    def save_session(self, user_id: str, session_data: Dict) -> None
    def load_session(self, user_id: str) -> Dict
    def is_session_valid(self, session_data: Dict) -> bool
    def clear_session(self, user_id: str) -> None
```

### 2. API客户端模块 (src/api/)

**vidu_client.py**
```python
class ViduClient:
    def __init__(self, base_url: str, session_manager: SessionManager)
    def upload_image(self, image_path: str) -> Dict[str, str]
    def submit_task(self, image_url: str, prompt: str, use_off_peak: bool) -> Dict
    def get_task_status(self, task_id: str) -> Dict
    def download_video(self, video_url: str, save_path: str) -> bool
    def get_off_peak_status(self) -> Dict[str, bool]
```

**request_handler.py**
```python
class RequestHandler:
    def __init__(self, anti_detection: AntiDetection)
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response
    def handle_rate_limit(self, response: requests.Response) -> None
    def simulate_human_behavior(self) -> None
```

### 3. 任务管理模块 (src/tasks/)

**task_manager.py**
```python
class TaskManager:
    def __init__(self, vidu_client: ViduClient, config: Dict)
    def add_task(self, image_path: str, prompt: str, priority: int) -> str
    def process_queue(self) -> None
    def retry_failed_tasks(self) -> None
    def get_task_history(self, days: int) -> List[Dict]
```

**scheduler.py**
```python
class TaskScheduler:
    def __init__(self, task_manager: TaskManager)
    def schedule_off_peak_check(self) -> None
    def schedule_daily_download(self) -> None
    def start_scheduler(self) -> None
    def stop_scheduler(self) -> None
```

### 4. 工具模块 (src/utils/)

**behavior_simulator.py**
```python
class BehaviorSimulator:
    def __init__(self, config: Dict)
    def random_delay(self, min_seconds: int, max_seconds: int) -> None
    def simulate_user_activity(self) -> None
    def generate_realistic_intervals(self) -> List[int]
```

**anti_detection.py**
```python
class AntiDetection:
    def __init__(self)
    def get_random_user_agent(self) -> str
    def get_proxy_config(self) -> Dict
    def add_request_headers(self, headers: Dict) -> Dict
    def handle_captcha(self, response: requests.Response) -> Dict
```

## 数据流程设计

### 任务提交流程
1. **图片预处理** → 压缩优化、格式转换
2. **错峰检测** → 检查当前是否为错峰时段
3. **任务排队** → 加入任务队列，设置优先级
4. **API调用** → 模拟用户行为提交任务
5. **状态追踪** → 记录任务ID和状态信息

### 结果检查流程
1. **定时触发** → 每日凌晨检查昨日任务
2. **状态查询** → 批量查询任务完成状态
3. **文件下载** → 下载已完成的视频文件
4. **结果整理** → 按日期和任务分类存储

## 配置文件规范

### config.json
```json
{
    "vidu": {
        "base_url": "https://www.vidu.com",
        "api_version": "v1",
        "off_peak_hours": [0, 1, 2, 3, 4, 5, 6],
        "max_retry_count": 3,
        "request_timeout": 30
    },
    "behavior": {
        "min_delay": 30,
        "max_delay": 120,
        "user_agents_file": "config/user_agents.txt",
        "use_proxy": false
    },
    "storage": {
        "input_dir": "data/input_images",
        "output_dir": "data/output_videos",
        "log_dir": "data/logs",
        "max_log_size": "10MB"
    },
    "scheduler": {
        "check_interval": 3600,
        "daily_check_time": "02:00",
        "enable_auto_download": true
    }
}
```

### accounts.json (加密存储)
```json
{
    "accounts": [
        {
            "id": "account_1",
            "username": "encrypted_username",
            "password": "encrypted_password",
            "is_premium": true,
            "last_login": "2024-12-20T10:00:00Z"
        }
    ]
}
```

## 错误处理策略

### 网络错误处理
- **连接超时**: 指数退避重试，最多3次
- **HTTP错误**: 根据状态码分类处理
- **限流处理**: 自动延长请求间隔

### 业务逻辑错误
- **认证失败**: 自动重新登录
- **任务失败**: 记录失败原因，人工干预
- **文件错误**: 验证文件完整性，重新下载

### 数据一致性保证
- **事务性操作**: 关键操作使用原子性保证
- **状态同步**: 定期与服务器状态同步
- **数据备份**: 重要数据多份备份

实施检查清单：
1. 创建项目目录结构和基础文件
2. 实现配置管理系统 (src/config/settings.py)
3. 开发日志系统 (src/utils/logger.py)
4. 实现反反爬策略模块 (src/utils/anti_detection.py)
5. 创建用户行为模拟器 (src/utils/behavior_simulator.py)
6. 开发HTTP请求处理器 (src/api/request_handler.py)
7. 实现会话管理器 (src/auth/session_manager.py)
8. 创建登录管理器 (src/auth/login_manager.py)
9. 开发vidu.com API客户端 (src/api/vidu_client.py)
10. 实现文件管理器 (src/utils/file_manager.py)
11. 创建任务管理器 (src/tasks/task_manager.py)
12. 开发状态检查器 (src/tasks/status_checker.py)
13. 实现任务调度器 (src/tasks/scheduler.py)
14. 创建主程序入口 (main.py)
15. 开发任务提交脚本 (scripts/submit_task.py)
16. 创建结果检查脚本 (scripts/check_results.py)
17. 实现每日定时检查脚本 (scripts/daily_checker.py)
18. 编写项目配置文件和依赖管理
19. 创建部署文档和使用说明
20. 进行集成测试和错误处理验证

# 当前执行步骤 (由 EXECUTE 模式在开始执行某步骤时更新)  
> 正在执行: "步骤3-8: 快速实现登录测试所需的核心模块"

# 任务进度 (由 EXECUTE 模式在每步完成后追加)
- [2024-12-20 当前时间]
  - 步骤：1. 创建项目目录结构和基础文件
  - 修改：
    - 创建了完整的src包结构 (src/__init__.py, src/auth/__init__.py, src/api/__init__.py, src/tasks/__init__.py, src/utils/__init__.py, src/config/__init__.py)
    - 创建了项目依赖文件 (requirements.txt) 
    - 创建了主配置文件 (config/config.json)
    - 建立了基础的包导入结构和模块定义
  - 更改摘要：建立了项目的基础架构和目录结构，包含所有必要的Python包初始化文件和配置文件
  - 原因：执行计划步骤 1
  - 阻碍：无
  - 用户确认状态：成功

- [2024-12-20 当前时间]
  - 步骤：2. 实现配置管理系统 (src/config/settings.py)
  - 修改：
    - 创建了配置管理系统 (src/config/settings.py) - 支持手机验证码登录的半自动化方案
    - 更新了主配置文件 (config/config.json) - 添加了authentication配置段
    - 创建了常量定义文件 (src/config/constants.py) - 包含登录方式、API端点、用户提示等常量
    - 实现了加密存储机制用于保护敏感信息（手机号、会话数据）
    - 支持三种登录模式：manual_sms（手动验证码）、auto_session（会话重用）、hybrid（混合模式）
  - 更改摘要：基于用户反馈的手机验证码登录要求，实现了支持交互式验证码输入的配置管理系统
  - 原因：执行计划步骤 2，并根据用户发现的vidu平台验证码登录要求进行适配
  - 阻碍：无
  - 用户确认状态：成功

- [2024-12-20 当前时间]
  - 步骤：3-8. 快速实现登录测试所需的核心模块
  - 修改：
    - 创建了日志系统 (src/utils/logger.py) - 支持控制台和文件日志，包含认证专用日志
    - 实现了会话管理器 (src/auth/session_manager.py) - 支持会话保存、加载、验证和清理
    - 开发了HTTP请求处理器 (src/api/request_handler.py) - 支持重试、延时、状态码处理
    - 创建了登录管理器 (src/auth/login_manager.py) - 支持手机验证码登录的交互式流程
    - 制作了登录测试脚本 (test_login.py) - 可以测试手机验证码登录功能
    - 实现了三种登录模式：manual_sms（手动验证码）、auto_session（会话重用）、hybrid（混合模式）
    - 采用模拟登录流程，用于测试用户体验和系统架构
  - 更改摘要：为解决用户提出的验证码登录测试需求，快速实现了核心认证模块，现在可以测试手机验证码登录流程
  - 原因：用户要求测试手机号17701058047的验证码登录功能，需要提前实现认证相关模块
  - 阻碍：无
  - 状态：待确认