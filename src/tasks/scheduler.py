"""
任务调度器 - 处理定时任务和自动化调度
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from src.config.constants import Constants
from src.utils.logger import get_logger

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, task_manager, status_checker, scheduler_config):
        self.task_manager = task_manager
        self.status_checker = status_checker
        self.scheduler_config = scheduler_config
        self.logger = get_logger("SCHEDULER")
        
        # 创建调度器
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.is_running = False
        self._jobs = {}
    
    def start(self) -> bool:
        """启动调度器"""
        try:
            if self.is_running:
                self.logger.warning("调度器已经在运行")
                return True
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            
            # 添加默认任务
            self._setup_default_jobs()
            
            self.logger.info("任务调度器启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"调度器启动失败: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """停止调度器"""
        try:
            if not self.is_running:
                self.logger.warning("调度器未在运行")
                return True
            
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            self._jobs.clear()
            
            self.logger.info("任务调度器已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"调度器停止失败: {str(e)}")
            return False
    
    def _setup_default_jobs(self) -> None:
        """设置默认调度任务"""
        try:
            # 1. 定期状态检查 (每小时一次)
            self.add_interval_job(
                func=self._periodic_status_check,
                job_id='periodic_status_check',
                minutes=self.scheduler_config.get('check_interval', 60) // 60,
                description='定期检查活跃任务状态'
            )
            
            # 2. 每日任务检查 (每天凌晨2点)
            daily_time = self.scheduler_config.get('daily_check_time', '02:00')
            hour, minute = map(int, daily_time.split(':'))
            
            self.add_cron_job(
                func=self._daily_task_check,
                job_id='daily_task_check',
                hour=hour,
                minute=minute,
                description='每日检查昨日任务并下载视频'
            )
            
            # 3. 错峰时段检查 (每5分钟检查一次错峰状态)
            self.add_interval_job(
                func=self._off_peak_check,
                job_id='off_peak_check',
                minutes=5,
                description='检查错峰时段状态'
            )
            
            # 4. 批量历史任务检查 (每30分钟检查一次)
            self.add_interval_job(
                func=self._batch_history_check,
                job_id='batch_history_check',
                minutes=30,
                description='批量检查历史任务并下载视频'
            )
            
            # 4. 缓存清理 (每周日凌晨3点)
            self.add_cron_job(
                func=self._weekly_cleanup,
                job_id='weekly_cleanup',
                day_of_week=6,  # 周日
                hour=3,
                minute=0,
                description='每周清理缓存和旧任务'
            )
            
            self.logger.info("默认调度任务设置完成")
            
        except Exception as e:
            self.logger.error(f"设置默认任务失败: {str(e)}")
    
    def add_cron_job(self, func: Callable, job_id: str, description: str = "", **cron_kwargs) -> bool:
        """添加定时任务 (cron风格)"""
        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=CronTrigger(**cron_kwargs),
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300  # 5分钟容错时间
            )
            
            self._jobs[job_id] = {
                'job': job,
                'description': description,
                'type': 'cron',
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"添加定时任务成功: {job_id} - {description}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加定时任务失败: {job_id} - {str(e)}")
            return False
    
    def add_interval_job(self, func: Callable, job_id: str, description: str = "", **interval_kwargs) -> bool:
        """添加间隔任务"""
        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(**interval_kwargs),
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300
            )
            
            self._jobs[job_id] = {
                'job': job,
                'description': description,
                'type': 'interval',
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"添加间隔任务成功: {job_id} - {description}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加间隔任务失败: {job_id} - {str(e)}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        try:
            if job_id in self._jobs:
                self.scheduler.remove_job(job_id)
                del self._jobs[job_id]
                self.logger.info(f"移除任务成功: {job_id}")
                return True
            else:
                self.logger.warning(f"任务不存在: {job_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"移除任务失败: {job_id} - {str(e)}")
            return False
    
    def get_job_status(self) -> Dict[str, Any]:
        """获取所有任务状态"""
        try:
            jobs_info = {}
            
            for job_id, job_info in self._jobs.items():
                job = job_info['job']
                jobs_info[job_id] = {
                    'description': job_info['description'],
                    'type': job_info['type'],
                    'created_at': job_info['created_at'],
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'is_active': True
                }
            
            return {
                'scheduler_running': self.is_running,
                'total_jobs': len(self._jobs),
                'jobs': jobs_info
            }
            
        except Exception as e:
            self.logger.error(f"获取任务状态失败: {str(e)}")
            return {
                'scheduler_running': self.is_running,
                'total_jobs': 0,
                'error': str(e)
            }
    
    def schedule_task_submission(self, image_path: str, prompt: str, 
                               scheduled_time: datetime, task_name: str = "") -> bool:
        """安排任务提交"""
        try:
            job_id = f"submit_task_{int(time.time())}"
            
            def submit_task():
                self.logger.info(f"执行预定任务提交: {task_name or job_id}")
                result = self.task_manager.create_video_task(image_path, prompt, use_off_peak=True)
                if result['success']:
                    self.logger.info(f"预定任务提交成功: {result['task_id']}")
                else:
                    self.logger.error(f"预定任务提交失败: {result['error']}")
            
            job = self.scheduler.add_job(
                func=submit_task,
                trigger='date',
                run_date=scheduled_time,
                id=job_id,
                misfire_grace_time=600  # 10分钟容错
            )
            
            self._jobs[job_id] = {
                'job': job,
                'description': f"预定任务提交: {task_name or ''}",
                'type': 'scheduled',
                'created_at': datetime.now().isoformat(),
                'image_path': image_path,
                'prompt': prompt
            }
            
            self.logger.info(f"任务提交已安排: {scheduled_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"安排任务提交失败: {str(e)}")
            return False
    
    def _periodic_status_check(self) -> None:
        """定期状态检查"""
        try:
            self.logger.debug("执行定期状态检查")
            result = self.status_checker.check_all_pending_tasks()
            
            if result.get('completed_count', 0) > 0:
                self.logger.info(f"定期检查发现 {result['completed_count']} 个完成的任务")
            
        except Exception as e:
            self.logger.error(f"定期状态检查异常: {str(e)}")
    
    def _daily_task_check(self) -> None:
        """每日任务检查"""
        try:
            self.logger.info("执行每日任务检查")
            result = self.status_checker.check_yesterday_tasks()
            
            if result.get('downloaded_count', 0) > 0:
                self.logger.info(f"每日检查下载了 {result['downloaded_count']} 个昨日视频")
            
        except Exception as e:
            self.logger.error(f"每日任务检查异常: {str(e)}")
    
    def _off_peak_check(self) -> None:
        """错峰时段检查"""
        try:
            current_hour = datetime.now().hour
            off_peak_hours = [0, 1, 2, 3, 4, 5, 6]  # 配置中获取
            
            if current_hour in off_peak_hours:
                # 检查是否有等待错峰的任务
                waiting_tasks = self.task_manager.get_tasks_by_status(Constants.TaskStatus.WAITING_OFF_PEAK)
                
                if waiting_tasks:
                    self.logger.info(f"进入错峰时段，发现 {len(waiting_tasks)} 个等待任务")
                    # 这里可以添加重新提交等待任务的逻辑
            
        except Exception as e:
            self.logger.error(f"错峰时段检查异常: {str(e)}")

    def _batch_history_check(self) -> None:
        """批量历史任务检查"""
        try:
            self.logger.info("执行定时批量历史任务检查")
            
            # 调用状态检查器的批量历史检查方法
            result = self.status_checker.check_history_tasks_batch(max_pages=3)
            
            if result.get('success'):
                downloaded = result.get('successful_downloads', 0)
                if downloaded > 0:
                    self.logger.info(f"批量历史检查完成，成功下载 {downloaded} 个视频")
                else:
                    self.logger.debug("批量历史检查完成，没有新的视频需要下载")
            else:
                error_msg = result.get('error', '未知错误')
                self.logger.error(f"批量历史检查失败: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"批量历史任务检查异常: {str(e)}")
    
    def _weekly_cleanup(self) -> None:
        """每周清理"""
        try:
            self.logger.info("执行每周清理")
            
            # 清理旧任务记录
            cleaned_tasks = self.task_manager.cleanup_old_tasks(30)  # 清理30天前的任务
            
            # 清理缓存文件
            from src.utils.file_manager import FileManager
            # 这里需要file_manager实例，暂时跳过
            
            self.logger.info(f"每周清理完成 - 清理任务: {cleaned_tasks}")
            
        except Exception as e:
            self.logger.error(f"每周清理异常: {str(e)}")
    
    def force_run_job(self, job_id: str) -> bool:
        """强制执行任务"""
        try:
            if job_id in self._jobs:
                job = self._jobs[job_id]['job']
                job.func()
                self.logger.info(f"强制执行任务成功: {job_id}")
                return True
            else:
                self.logger.error(f"任务不存在: {job_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"强制执行任务失败: {job_id} - {str(e)}")
            return False
