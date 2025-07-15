#!/usr/bin/env python3
"""
任务提交脚本 - 简化的任务提交工具
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import AutoGenVideoApp

def main():
    """主函数"""
    if len(sys.argv) < 4:
        print("使用方法: python submit_task.py <手机号> <图片路径> <提示词>")
        print("示例: python submit_task.py 17701058047 image.jpg '生成一个美丽的风景视频'")
        return
    
    phone = sys.argv[1]
    image_path = sys.argv[2]
    prompt = sys.argv[3]
    
    # 检查图片文件是否存在
    if not Path(image_path).exists():
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    print("=" * 60)
    print("🎯 autoGenVideo - 任务提交工具")
    print("=" * 60)
    
    # 创建应用实例
    app = AutoGenVideoApp()
    
    # 初始化系统
    if not app.initialize():
        print("❌ 系统初始化失败")
        return
    
    # 智能登录检查
    if app.is_logged_in:
        print("🎯 检测到本地token，已自动登录成功")
        print("✅ 跳过SMS验证，直接使用已有认证")
    else:
        print("🔑 本地无有效token，开始SMS验证登录...")
        if not app.login(phone):
            print("❌ 登录失败")
            return
    
    # 提交任务
    result = app.submit_task(image_path, prompt, use_off_peak=True)
    
    if result['success']:
        print(f"\n🎉 任务提交成功！")
        print(f"📝 任务ID: {result['task_id']}")
        print(f"💡 您可以使用以下命令检查任务状态:")
        print(f"   python main.py check")
        print(f"💡 或者启动自动监控:")
        print(f"   python main.py monitor")
    else:
        print(f"\n❌ 任务提交失败: {result['error']}")

if __name__ == "__main__":
    main()
