#!/usr/bin/env python3
"""
autoGenVideo - 主程序入口
Vidu平台自动化图生视频工具
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import Settings
from src.auth.login_manager import LoginManager
from src.api.request_handler import RequestHandler
from src.utils.file_manager import FileManager
from src.tasks.task_manager import TaskManager
from src.tasks.status_checker import StatusChecker
from src.tasks.scheduler import TaskScheduler
from src.utils.logger import get_logger

class AutoGenVideoApp:
    """主应用程序类"""
    
    def __init__(self):
        self.settings = None
        self.login_manager = None
        self.request_handler = None
        self.file_manager = None
        self.task_manager = None
        self.status_checker = None
        self.scheduler = None
        self.logger = get_logger("MAIN")
        
        self.is_initialized = False
        self.is_logged_in = False
    
    def initialize(self) -> bool:
        """初始化系统组件"""
        try:
            self.logger.info("初始化autoGenVideo系统...")
            
            # 1. 加载配置
            self.settings = Settings()
            vidu_config = self.settings.get_vidu_config()
            auth_config = self.settings.get_auth_config()
            behavior_config = self.settings.get_behavior_config()
            storage_paths = self.settings.get_storage_paths()
            
            # 2. 初始化请求处理器
            self.request_handler = RequestHandler(vidu_config.base_url)
            
            # 3. 初始化登录管理器
            self.login_manager = LoginManager(self.settings)
            
            # 4. 初始化文件管理器
            self.file_manager = FileManager(self.request_handler, storage_paths)
            
            # 5. 初始化任务管理器
            self.task_manager = TaskManager(
                self.request_handler,
                self.file_manager,
                storage_paths
            )
            
            # 6. 初始化状态检查器
            self.status_checker = StatusChecker(
                self.task_manager,
                behavior_config
            )
            
            # 7. 初始化调度器
            scheduler_config = {
                'check_interval': 3600,  # 1小时
                'daily_check_time': '02:00'
            }
            self.scheduler = TaskScheduler(
                self.task_manager,
                self.status_checker,
                scheduler_config
            )
            
            self.is_initialized = True
            self.logger.info("系统初始化成功")
            
            # 自动检查并加载token
            self._auto_load_token()
            
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {str(e)}")
            return False
    
    def login(self, phone: str) -> bool:
        """登录系统"""
        try:
            if not self.is_initialized:
                self.logger.error("系统未初始化")
                return False
            
            self.logger.info(f"开始登录 - 手机号: {phone}")
            
            result = self.login_manager.login(phone)
            if result['success']:
                self.is_logged_in = True
                self.logger.info("登录成功")
                
                # 同步JWT token到主应用的request_handler
                session_data = result.get('session_data', {})
                access_token = session_data.get('access_token')
                if access_token:
                    self.request_handler.set_auth_cookie(access_token)
                    self.logger.info("JWT认证信息已同步到主request_handler")
                else:
                    self.logger.warning("登录响应中未找到access_token")
                
                # 显示用户信息
                user_info = result.get('session_data', {}).get('user_info', {})
                print(f"\n✅ 登录成功！")
                print(f"👤 用户: {user_info.get('nickname', '未知')}")
                print(f"💎 用户ID: {user_info.get('id', '未知')}")
                print(f"📱 手机号: {user_info.get('phone', '未知')}")
                print(f"🎯 订阅计划: {user_info.get('subs_plan', '未知')}")
                
                return True
            else:
                self.logger.error(f"登录失败: {result['error']}")
                print(f"\n❌ 登录失败: {result['error']}")
                return False
                
        except Exception as e:
            self.logger.error(f"登录异常: {str(e)}")
            return False
    
    def submit_task(self, image_path: str, prompt: str, use_off_peak: bool = True) -> Dict[str, Any]:
        """提交视频生成任务"""
        try:
            if not self.is_logged_in:
                return {
                    'success': False,
                    'error': '请先登录'
                }
            
            self.logger.info(f"提交任务 - 图片: {image_path}, 提示词: {prompt}")
            
            result = self.task_manager.create_video_task(image_path, prompt, use_off_peak)
            
            if result['success']:
                print(f"\n✅ 任务提交成功！")
                print(f"🆔 任务ID: {result['task_id']}")
                print(f"📝 提示词: {prompt}")
                print(f"🖼️ 图片: {image_path}")
                print(f"⏰ 错峰模式: {'是' if use_off_peak else '否'}")
            else:
                print(f"\n❌ 任务提交失败: {result['error']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"任务提交异常: {str(e)}")
            return {
                'success': False,
                'error': f'任务提交异常: {str(e)}'
            }
    
    def check_tasks(self) -> Dict[str, Any]:
        """检查所有任务状态"""
        try:
            if not self.is_logged_in:
                return {
                    'success': False,
                    'error': '请先登录'
                }
            
            self.logger.info("检查所有任务状态")
            
            result = self.status_checker.check_all_pending_tasks()
            
            print(f"\n📊 任务状态检查结果:")
            print(f"🔍 检查任务数: {result.get('checked_count', 0)}")
            print(f"✅ 完成任务数: {result.get('completed_count', 0)}")
            print(f"❌ 失败任务数: {result.get('failed_count', 0)}")
            print(f"⏳ 进行中任务数: {result.get('still_processing_count', 0)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"状态检查异常: {str(e)}")
            return {
                'success': False,
                'error': f'状态检查异常: {str(e)}'
            }
    
    def start_monitoring(self) -> bool:
        """开始任务监控"""
        try:
            if not self.is_logged_in:
                print("❌ 请先登录")
                return False
            
            print("\n🚀 启动任务调度器...")
            
            if self.scheduler.start():
                print("✅ 调度器启动成功")
                print("📅 已设置每日任务检查（凌晨2点）")
                print("⏰ 已设置定期状态检查（每小时）")
                print("🌙 已设置错峰时段监控（每5分钟）")
                print("\n💡 调度器将在后台运行，使用 Ctrl+C 停止")
                return True
            else:
                print("❌ 调度器启动失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动监控异常: {str(e)}")
            return False
    
    def stop_monitoring(self) -> bool:
        """停止任务监控"""
        try:
            if self.scheduler and self.scheduler.is_running:
                self.scheduler.stop()
                print("🛑 调度器已停止")
                return True
            else:
                print("💡 调度器未在运行")
                return False
                
        except Exception as e:
            self.logger.error(f"停止监控异常: {str(e)}")
            return False
    
    def show_status(self) -> None:
        """显示系统状态"""
        try:
            print(f"\n📈 系统状态:")
            print(f"🔧 初始化状态: {'✅ 已初始化' if self.is_initialized else '❌ 未初始化'}")
            print(f"🔑 登录状态: {'✅ 已登录' if self.is_logged_in else '❌ 未登录'}")
            
            if self.scheduler:
                scheduler_status = self.scheduler.get_job_status()
                print(f"⏰ 调度器状态: {'🟢 运行中' if scheduler_status['scheduler_running'] else '🔴 已停止'}")
                print(f"📋 调度任务数: {scheduler_status['total_jobs']}")
            
            if self.task_manager:
                all_tasks = self.task_manager.get_all_tasks()
                recent_tasks = self.task_manager.get_recent_tasks(7)
                print(f"📊 总任务数: {len(all_tasks)}")
                print(f"📅 近7天任务: {len(recent_tasks)}")
            
            if self.file_manager:
                storage_info = self.file_manager.get_storage_info()
                for name, info in storage_info.items():
                    print(f"💾 {name}: {info['file_count']}个文件, {info['total_size_mb']}MB")
            
        except Exception as e:
            self.logger.error(f"显示状态异常: {str(e)}")

    def show_task_records(self) -> None:
        """显示任务ID记录"""
        try:
            if not self.is_initialized:
                print("❌ 系统未初始化")
                return
            
            if self.task_manager:
                self.task_manager.show_task_ids_summary()
            else:
                print("❌ 任务管理器未初始化")
                
        except Exception as e:
            self.logger.error(f"显示任务记录异常: {str(e)}")

    def _auto_load_token(self):
        """自动检查并加载token"""
        try:
            self.logger.info("尝试自动加载token...")
            
            # 尝试使用LoginManager的token登录功能
            result = self.login_manager.try_token_login()
            if result['success']:
                self.is_logged_in = True
                
                # 同步JWT token到主应用的request_handler
                session_data = result.get('session_data', {})
                access_token = session_data.get('access_token')
                if access_token:
                    self.request_handler.set_auth_cookie(access_token)
                    self.logger.info("Token自动登录成功，JWT认证信息已同步")
                    
                    # 显示自动登录信息
                    user_info = session_data.get('user_info', {})
                    self.logger.info(f"自动登录用户: {user_info.get('nickname', '未知')}")
                    return True
            else:
                self.logger.info(f"Token自动登录失败: {result.get('error', '未知错误')}")
                return False
            
        except Exception as e:
            self.logger.error(f"自动加载token失败: {str(e)}")
            return False

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='autoGenVideo - Vidu平台自动化图生视频工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py login 17701058047                    # 登录
  python main.py submit image.jpg "生成一个美丽的风景"    # 提交任务
  python main.py check                                # 检查任务状态
  python main.py monitor                              # 开始监控
  python main.py status                               # 显示系统状态
  python main.py tasks                                # 显示任务ID记录
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 登录命令
    login_parser = subparsers.add_parser('login', help='登录到vidu平台')
    login_parser.add_argument('phone', help='手机号码')
    
    # 提交任务命令
    submit_parser = subparsers.add_parser('submit', help='提交视频生成任务')
    submit_parser.add_argument('image', help='图片文件路径')
    submit_parser.add_argument('prompt', help='视频生成提示词')
    submit_parser.add_argument('--no-off-peak', action='store_true', help='不使用错峰模式')
    
    # 检查任务命令
    subparsers.add_parser('check', help='检查任务状态')
    
    # 监控命令
    subparsers.add_parser('monitor', help='开始任务监控')
    
    # 状态命令
    subparsers.add_parser('status', help='显示系统状态')
    
    # 任务ID记录命令
    subparsers.add_parser('tasks', help='显示任务ID记录')
    
    # 批量历史检查命令
    history_parser = subparsers.add_parser('history', help='批量检查历史任务并下载视频')
    history_parser.add_argument('--max-pages', type=int, default=5, help='最大查询页数 (默认: 5)')
    history_parser.add_argument('--download-only', action='store_true', help='仅下载视频，不显示详细信息')
    
    # 批量提交命令
    batch_parser = subparsers.add_parser('batch-submit', help='批量提交图生视频任务')
    batch_parser.add_argument('--images-dir', default='data/input_images', help='图片目录路径 (默认: data/input_images)')
    batch_parser.add_argument('--prompts-file', default='data/input_images/prompt.txt', help='提示词文件路径 (默认: data/input_images/prompt.txt)')
    batch_parser.add_argument('--task-delay', type=float, default=5.0, help='任务间延时秒数 (默认: 5.0)')
    batch_parser.add_argument('--no-confirm', action='store_true', help='跳过确认直接开始批量提交')
    batch_parser.add_argument('--use-off-peak', action='store_true', help='使用错峰模式 (默认: 不使用)')
    
    return parser

def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建应用实例
    app = AutoGenVideoApp()
    
    # 初始化系统
    if not app.initialize():
        print("❌ 系统初始化失败")
        return
    
    try:
        if args.command == 'login':
            app.login(args.phone)
            
        elif args.command == 'submit':
            # 提交任务需要先登录
            if app.is_logged_in:
                print("📝 检测到已登录状态，直接提交任务...")
                app.submit_task(args.image, args.prompt, not args.no_off_peak)
            else:
                print("📝 提交任务需要先登录，请输入手机号:")
                phone = input("手机号: ").strip()
                if app.login(phone):
                    app.submit_task(args.image, args.prompt, not args.no_off_peak)
            
        elif args.command == 'check':
            # 检查任务需要先登录
            if app.is_logged_in:
                print("🔍 检测到已登录状态，直接检查任务...")
                app.check_tasks()
            else:
                print("🔍 检查任务需要先登录，请输入手机号:")
                phone = input("手机号: ").strip()
                if app.login(phone):
                    app.check_tasks()
            
        elif args.command == 'monitor':
            # 监控需要先登录
            if app.is_logged_in:
                print("📊 检测到已登录状态，直接开始监控...")
                if app.start_monitoring():
                    try:
                        # 保持程序运行
                        import time
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print("\n\n🛑 收到停止信号...")
                        app.stop_monitoring()
            else:
                print("📊 开始监控需要先登录，请输入手机号:")
                phone = input("手机号: ").strip()
                if app.login(phone):
                    if app.start_monitoring():
                        try:
                            # 保持程序运行
                            import time
                            while True:
                                time.sleep(1)
                        except KeyboardInterrupt:
                            print("\n\n🛑 收到停止信号...")
                            app.stop_monitoring()
            
        elif args.command == 'status':
            app.show_status()
            
        elif args.command == 'tasks':
            app.show_task_records()
            
        elif args.command == 'history':
            # 批量历史检查需要先登录
            if not app.is_logged_in:
                print("❌ 批量历史检查需要先登录")
                return
            
            print(f"\n🔍 开始批量历史任务检查 (最大页数: {args.max_pages})...")
            
            if args.download_only:
                # 仅下载模式
                result = app.status_checker.download_pending_videos()
                
                if result.get('success'):
                    downloaded = result.get('successful_downloads', 0)
                    total_downloadable = result.get('downloadable_count', 0)
                    
                    print(f"✅ 视频下载完成")
                    print(f"📊 可下载视频: {total_downloadable}")
                    print(f"⬇️ 成功下载: {downloaded}")
                    
                    if result.get('failed_downloads', 0) > 0:
                        print(f"❌ 下载失败: {result['failed_downloads']}")
                else:
                    print(f"❌ 视频下载失败: {result.get('error', '未知错误')}")
            else:
                # 完整批量检查模式
                result = app.status_checker.check_history_tasks_batch(max_pages=args.max_pages)
                
                if result.get('success'):
                    print(f"✅ 批量历史检查完成")
                    print(f"📊 检查结果:")
                    print(f"   📡 获取历史任务: {result.get('history_tasks_fetched', 0)}")
                    print(f"   📁 本地任务记录: {result.get('local_tasks_count', 0)}")
                    print(f"   🔗 匹配任务: {result.get('matched_count', 0)}")
                    print(f"   ✅ 已完成任务: {result.get('completed_count', 0)}")
                    print(f"   📥 可下载任务: {result.get('downloadable_count', 0)}")
                    print(f"   ⬇️ 成功下载: {result.get('successful_downloads', 0)}")
                    
                    if result.get('failed_downloads', 0) > 0:
                        print(f"   ❌ 下载失败: {result['failed_downloads']}")
                    
                    # 显示未匹配的任务
                    unmatched_local = result.get('unmatched_local', [])
                    unmatched_remote = result.get('unmatched_remote', [])
                    
                    if unmatched_local:
                        print(f"\n⚠️  本地未匹配任务 ({len(unmatched_local)}个): {', '.join(list(unmatched_local)[:5])}")
                        if len(unmatched_local) > 5:
                            print(f"    (还有 {len(unmatched_local) - 5} 个...)")
                    
                    if unmatched_remote:
                        print(f"\n📡 远程未匹配任务 ({len(unmatched_remote)}个): {', '.join(list(unmatched_remote)[:5])}")
                        if len(unmatched_remote) > 5:
                            print(f"    (还有 {len(unmatched_remote) - 5} 个...)")
                            
                else:
                    print(f"❌ 批量历史检查失败: {result.get('error', '未知错误')}")
                    
        elif args.command == 'batch-submit':
            # 批量提交需要先登录
            if not app.is_logged_in:
                print("❌ 批量提交需要先登录")
                return
            
            print(f"\n🚀 准备批量提交图生视频任务")
            print(f"📁 图片目录: {args.images_dir}")
            print(f"📝 提示词文件: {args.prompts_file}")
            print(f"⏱️ 任务间延时: {args.task_delay}秒")
            print(f"🏔️ 错峰模式: {'是' if args.use_off_peak else '否'}")
            
            # 预检查文件
            try:
                from pathlib import Path
                
                images_path = Path(args.images_dir)
                prompts_path = Path(args.prompts_file)
                
                if not images_path.exists():
                    print(f"❌ 图片目录不存在: {args.images_dir}")
                    return
                
                if not prompts_path.exists():
                    print(f"❌ 提示词文件不存在: {args.prompts_file}")
                    return
                
                # 快速预览
                print(f"\n🔍 预检查文件...")
                
                # 检查图片文件
                image_files = [f for f in images_path.iterdir() 
                              if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']]
                
                if not image_files:
                    print(f"❌ 在图片目录中未找到图片文件")
                    return
                
                print(f"📸 找到 {len(image_files)} 个图片文件")
                
                # 检查提示词
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    prompts = [line.strip() for line in f.read().strip().split('\n') if line.strip()]
                
                if not prompts:
                    print(f"❌ 提示词文件为空或无有效内容")
                    return
                
                print(f"💭 找到 {len(prompts)} 个提示词")
                
                # 显示配对信息
                min_count = min(len(image_files), len(prompts))
                print(f"🎯 将创建 {min_count} 个视频任务")
                
                if len(image_files) != len(prompts):
                    print(f"⚠️  图片数量与提示词数量不匹配，将处理前{min_count}个")
                
                # 用户确认
                if not args.no_confirm:
                    print(f"\n⚠️  即将开始批量提交任务，请确认:")
                    print(f"   - 将创建 {min_count} 个视频任务")
                    print(f"   - 预计耗时约 {min_count * (args.task_delay + 10)} 秒")
                    print(f"   - 错峰模式: {'开启' if args.use_off_peak else '关闭'}")
                    
                    confirm = input(f"\n确认开始批量提交? (y/N): ").strip().lower()
                    if confirm not in ['y', 'yes', '是']:
                        print("❌ 用户取消批量提交")
                        return
                
                # 开始批量提交
                print(f"\n🎬 开始批量提交视频任务...")
                print("=" * 60)
                
                result = app.task_manager.batch_create_video_tasks(
                    images_dir=args.images_dir,
                    prompts_file=args.prompts_file,
                    use_off_peak=args.use_off_peak,
                    task_delay=args.task_delay
                )
                
                print("=" * 60)
                
                if result.get('success'):
                    print(f"✅ 批量提交完成!")
                    print(f"📊 提交结果:")
                    print(f"   📈 总任务数: {result.get('total_tasks', 0)}")
                    print(f"   ✅ 成功任务: {result.get('successful_tasks', 0)}")
                    print(f"   ❌ 失败任务: {result.get('failed_tasks', 0)}")
                    print(f"   📊 成功率: {result.get('success_rate', 0):.1f}%")
                    
                    if result.get('created_task_ids'):
                        print(f"\n🆔 创建的任务ID:")
                        for i, task_id in enumerate(result['created_task_ids'], 1):
                            print(f"   {i}. {task_id}")
                    
                    if result.get('errors'):
                        print(f"\n❌ 失败原因:")
                        for error in result['errors'][:5]:  # 只显示前5个错误
                            print(f"   - {error}")
                        if len(result['errors']) > 5:
                            print(f"   ... 还有 {len(result['errors']) - 5} 个错误")
                    
                    print(f"\n💡 建议:")
                    print(f"   - 使用 'python main.py check' 检查任务状态")
                    print(f"   - 使用 'python main.py history' 批量下载完成的视频")
                    
                else:
                    print(f"❌ 批量提交失败: {result.get('error', '未知错误')}")
                
            except Exception as e:
                print(f"❌ 批量提交过程中出错: {str(e)}")
            
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {str(e)}")
    finally:
        # 清理资源
        if app.scheduler and app.scheduler.is_running:
            app.stop_monitoring()

if __name__ == "__main__":
    main()
