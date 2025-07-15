#!/usr/bin/env python3
"""
系统功能测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import AutoGenVideoApp

def test_system():
    """测试系统基本功能"""
    print("=" * 60)
    print("🧪 autoGenVideo 系统功能测试")
    print("=" * 60)
    
    # 创建应用实例
    app = AutoGenVideoApp()
    
    # 测试初始化
    print("\n🔧 测试系统初始化...")
    if app.initialize():
        print("✅ 系统初始化成功")
    else:
        print("❌ 系统初始化失败")
        return
    
    # 显示系统状态
    print("\n📊 系统状态:")
    app.show_status()
    
    # 测试模块导入
    print("\n📦 测试模块导入...")
    try:
        from src.config.settings import Settings
        from src.auth.login_manager import LoginManager
        from src.utils.file_manager import FileManager
        from src.tasks.task_manager import TaskManager
        from src.tasks.status_checker import StatusChecker
        from src.tasks.scheduler import TaskScheduler
        print("✅ 所有核心模块导入成功")
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return
    
    # 测试配置加载
    print("\n⚙️ 测试配置加载...")
    try:
        settings = Settings()
        vidu_config = settings.get_vidu_config()
        auth_config = settings.get_auth_config()
        behavior_config = settings.get_behavior_config()
        print(f"✅ 配置加载成功")
        print(f"   - Vidu API: {vidu_config.base_url}")
        print(f"   - 登录方式: {auth_config.login_method}")
        print(f"   - 延时范围: {behavior_config.min_delay}-{behavior_config.max_delay}秒")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return
    
    # 测试存储路径
    print("\n💾 测试存储路径...")
    try:
        storage_paths = settings.get_storage_paths()
        for name, path in storage_paths.items():
            exists = "✅" if path.exists() else "❌"
            print(f"   {exists} {name}: {path}")
        print("✅ 存储路径检查完成")
    except Exception as e:
        print(f"❌ 存储路径检查失败: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 系统功能测试完成！")
    print("💡 提示：")
    print("   - 使用 'python main.py login <手机号>' 来登录")
    print("   - 使用 'python main.py status' 来查看系统状态")
    print("   - 使用 'python main.py --help' 来查看所有可用命令")
    print("=" * 60)

if __name__ == "__main__":
    test_system()
