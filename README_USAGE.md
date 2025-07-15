# autoGenVideo 使用指南

## 系统概述

autoGenVideo 是一个针对 Vidu 平台的自动化图生视频工具，支持：

- ✅ 真实API登录（手机验证码）
- 🖼️ 图片上传和处理
- 🎬 视频生成任务管理
- ⏰ 错峰模式自动化
- 📊 任务状态监控
- 📅 定时任务调度
- 💾 自动视频下载

## 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
source venv/bin/activate

# 验证系统状态
python test_system.py
```

### 2. 登录测试

```bash
# 测试登录功能
python test_login.py 17701058047
```

### 3. 查看系统状态

```bash
# 查看当前系统状态
python main.py status
```

## 主要功能

### 登录

```bash
# 登录到 Vidu 平台
python main.py login 17701058047
```

### 提交任务

```bash
# 提交图生视频任务
python main.py submit image.jpg "生成一个美丽的风景视频"

# 或使用简化脚本
python scripts/submit_task.py 17701058047 image.jpg "生成一个美丽的风景视频"
```

### 检查任务状态

```bash
# 检查所有任务状态
python main.py check
```

### 启动自动监控

```bash
# 启动后台监控（自动检查任务状态和下载视频）
python main.py monitor
```

## 系统特性

### 🔐 认证系统
- 支持手机验证码登录
- 自动会话管理和刷新
- 加密存储敏感信息

### 🖼️ 图片处理
- 支持多种图片格式（JPG, PNG, WebP等）
- 自动压缩和格式优化
- 分辨率自适应调整

### 🎬 任务管理
- 批量任务提交
- 实时状态监控
- 失败任务重试

### ⏰ 智能调度
- 错峰时段自动检测
- 定时任务调度
- 每日自动检查昨日任务

### 💾 文件管理
- 自动视频下载
- 本地缓存管理
- 文件完整性验证

## 配置说明

### 主配置文件：`config/config.json`

```json
{
    "vidu": {
        "base_url": "https://service.vidu.cn",
        "off_peak_hours": [0, 1, 2, 3, 4, 5, 6]
    },
    "authentication": {
        "login_method": "manual_sms",
        "session_persistence": true,
        "interactive_login": true
    },
    "behavior": {
        "min_delay": 30,
        "max_delay": 120
    }
}
```

### 存储目录

- `data/input_images/` - 输入图片
- `data/output_videos/` - 输出视频
- `data/logs/` - 日志文件
- `data/cache/` - 缓存文件

## 高级用法

### 错峰模式

系统自动检测错峰时段（默认：凌晨0-6点），在错峰时段提交任务可以免费生成视频。

### 批量处理

```python
# 批量提交任务示例
from main import AutoGenVideoApp

app = AutoGenVideoApp()
app.initialize()
app.login("17701058047")

images = ["image1.jpg", "image2.jpg", "image3.jpg"]
prompts = ["提示词1", "提示词2", "提示词3"]

for image, prompt in zip(images, prompts):
    result = app.submit_task(image, prompt)
    print(f"任务 {result['task_id']} 提交{'成功' if result['success'] else '失败'}")
```

### 定时任务

系统自动设置以下定时任务：

- **每小时检查**: 检查活跃任务状态
- **每日凌晨2点**: 检查昨日任务并下载视频
- **每5分钟**: 检查错峰时段状态
- **每周日凌晨3点**: 清理缓存和旧任务

## 故障排除

### 常见问题

1. **登录失败**
   - 检查手机号格式
   - 确认验证码输入正确
   - 检查网络连接

2. **任务提交失败**
   - 确认已登录
   - 检查图片文件是否存在
   - 验证图片格式和大小

3. **下载失败**
   - 检查存储空间
   - 验证网络连接
   - 查看错误日志

### 日志查看

```bash
# 查看主日志
tail -f data/logs/autoGenVideo.log

# 查看错误日志
tail -f data/logs/autoGenVideo_error.log

# 查看认证日志
tail -f data/logs/auth.log
```

## 开发和扩展

### 添加新功能

系统采用模块化设计，可以轻松扩展：

- `src/auth/` - 认证相关
- `src/api/` - API通信
- `src/tasks/` - 任务管理
- `src/utils/` - 工具函数
- `src/config/` - 配置管理

### API 端点

当前支持的API端点：

- 发送验证码: `/iam/v1/users/send-auth-code`
- 用户登录: `/iam/v1/users/login`
- 图片上传: `/vidu/v1/upload/image`
- 创建任务: `/vidu/v1/tasks/create`
- 任务状态: `/vidu/v1/tasks/{task_id}/status`

## 支持

如有问题或建议，请查看：

1. 系统日志文件
2. 配置文件设置
3. 网络连接状态
4. API响应详情

---

**注意**: 本工具仅供学习和研究用途，请遵守 Vidu 平台的使用条款。
