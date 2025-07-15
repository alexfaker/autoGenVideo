#!/usr/bin/env python3
"""
Vidu平台登录测试脚本
测试手机验证码登录功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.auth.login_manager import LoginManager
from src.utils.logger import get_logger

def test_login(phone: str):
    """测试登录功能"""
    print("=" * 60)
    print("🎯 Vidu平台自动化工具 - 登录测试")
    print("=" * 60)
    
    try:
        # 初始化配置和组件
        print("🔧 初始化系统组件...")
        settings = Settings()
        login_manager = LoginManager(settings)
        logger = get_logger("TEST")
        
        print(f"✅ 系统初始化完成")
        print(f"📱 测试手机号: {phone}")
        
        # 显示当前配置
        auth_config = settings.get_auth_config()
        print(f"🔐 登录模式: {auth_config.login_method}")
        print(f"💾 会话保存: {'启用' if auth_config.auto_save_session else '禁用'}")
        print(f"🔄 交互式登录: {'启用' if auth_config.interactive_login else '禁用'}")
        
        # 执行登录测试
        print(f"\n🚀 开始登录测试...")
        login_result = login_manager.login(phone)
        
        # 显示登录结果
        print(f"\n" + "=" * 60)
        if login_result['success']:
            print(f"✅ 登录测试成功！")
            print(f"🔑 登录方式: {login_result['method']}")
            if login_result.get('message'):
                print(f"💬 消息: {login_result['message']}")
            
            # 显示会话信息
            session_data = login_result.get('session_data', {})
            user_info = session_data.get('user_info', {})
            if user_info:
                print(f"\n👤 用户信息:")
                print(f"   📱 手机号: {user_info.get('phone', '未知')}")
                print(f"   🆔 用户ID: {user_info.get('user_id', '未知')}")
                print(f"   👥 昵称: {user_info.get('nickname', '未知')}")
                print(f"   💎 会员状态: {'旗舰版' if user_info.get('is_premium') else '普通用户'}")
            
            # 测试会话管理
            print(f"\n🔍 测试会话管理功能...")
            session_info = login_manager.session_manager.get_session_info(phone)
            if session_info:
                print(f"✅ 会话信息获取成功:")
                print(f"   ⏰ 创建时间: {session_info['created_at']}")
                print(f"   ⏳ 过期时间: {session_info['expires_at']}")
                print(f"   ✔️  会话状态: {'有效' if session_info['is_valid'] else '无效'}")
            
            # 询问是否测试第二次登录（会话重用）
            print(f"\n💡 想要测试会话重用功能吗？")
            test_session = input("输入 'y' 进行第二次登录测试（应该会使用保存的会话）: ").strip().lower()
            
            if test_session == 'y':
                print(f"\n🔄 执行第二次登录测试...")
                # 临时切换到混合模式以测试会话重用
                original_method = auth_config.login_method
                auth_config.login_method = "hybrid"
                
                second_result = login_manager.login(phone)
                
                if second_result['success'] and second_result['method'] == 'session':
                    print(f"✅ 会话重用测试成功！")
                else:
                    print(f"⚠️  会话重用测试失败，使用了其他登录方式")
                
                # 恢复原始配置
                auth_config.login_method = original_method
            
        else:
            print(f"❌ 登录测试失败")
            print(f"🔴 错误: {login_result.get('error', '未知错误')}")
            print(f"📋 错误代码: {login_result.get('error_code', 'UNKNOWN')}")
        
        print(f"=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程发生异常: {str(e)}")
        logger.error(f"登录测试异常: {str(e)}")

def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        phone = sys.argv[1]
    else:
        phone = "17701058047"  # 用户提供的测试手机号
    
    # 验证手机号格式
    import re
    if not re.match(r'^1[3-9]\d{9}$', phone):
        print(f"❌ 手机号格式不正确: {phone}")
        print(f"💡 使用方法: python test_login.py [手机号]")
        print(f"💡 示例: python test_login.py 17701058047")
        return
    
    # 执行测试
    test_login(phone)

if __name__ == "__main__":
    main() 