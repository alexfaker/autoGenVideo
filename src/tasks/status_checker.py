"""
任务状态检查器 - 定期检查任务状态并处理完成的任务
"""

import time
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.config.constants import Constants
from src.utils.logger import get_logger

class StatusChecker:
    """任务状态检查器"""
    
    def __init__(self, task_manager, behavior_config):
        self.task_manager = task_manager
        self.behavior_config = behavior_config
        self.logger = get_logger("STATUS_CHECKER")
        self.is_running = False
    
    def check_all_pending_tasks(self) -> Dict[str, Any]:
        """检查所有待处理任务的状态"""
        try:
            pending_tasks = self.task_manager.get_tasks_by_status(Constants.TaskStatus.PENDING)
            processing_tasks = self.task_manager.get_tasks_by_status(Constants.TaskStatus.PROCESSING)
            
            all_active_tasks = {**pending_tasks, **processing_tasks}
            
            if not all_active_tasks:
                self.logger.info("没有待检查的活跃任务")
                return {
                    'checked_count': 0,
                    'completed_count': 0,
                    'failed_count': 0,
                    'still_processing_count': 0
                }
            
            self.logger.info(f"开始检查 {len(all_active_tasks)} 个活跃任务")
            
            results = {
                'checked_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'still_processing_count': 0,
                'completed_tasks': [],
                'failed_tasks': []
            }
            
            for task_id in all_active_tasks:
                # 模拟人类行为间隔
                self._simulate_human_delay()
                
                # 检查任务状态
                status_result = self.task_manager.check_task_status(task_id)
                results['checked_count'] += 1
                
                if status_result['success']:
                    status = status_result['status']
                    
                    if status == Constants.TaskStatus.COMPLETED:
                        results['completed_count'] += 1
                        results['completed_tasks'].append(task_id)
                        self.logger.info(f"任务完成: {task_id}")
                        
                        # 自动下载完成的视频
                        self._auto_download_video(task_id)
                        
                    elif status == Constants.TaskStatus.FAILED:
                        results['failed_count'] += 1
                        results['failed_tasks'].append(task_id)
                        self.logger.warning(f"任务失败: {task_id}")
                        
                    elif status in [Constants.TaskStatus.PENDING, Constants.TaskStatus.PROCESSING]:
                        results['still_processing_count'] += 1
                        self.logger.debug(f"任务进行中: {task_id}, 状态: {status}")
                else:
                    self.logger.error(f"检查任务状态失败: {task_id}")
            
            self.logger.info(f"状态检查完成 - 检查: {results['checked_count']}, "
                           f"完成: {results['completed_count']}, "
                           f"失败: {results['failed_count']}, "
                           f"进行中: {results['still_processing_count']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量状态检查异常: {str(e)}")
            return {
                'error': str(e),
                'checked_count': 0
            }
    
    def check_yesterday_tasks(self) -> Dict[str, Any]:
        """检查昨日任务状态"""
        try:
            yesterday = datetime.now() - timedelta(days=1)
            start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 获取昨日任务
            all_tasks = self.task_manager.get_all_tasks()
            yesterday_tasks = {}
            
            for task_id, task_info in all_tasks.items():
                created_at = datetime.fromisoformat(task_info['created_at'])
                if start_time <= created_at <= end_time:
                    yesterday_tasks[task_id] = task_info
            
            if not yesterday_tasks:
                self.logger.info("昨日没有任务")
                return {
                    'date': yesterday.strftime('%Y-%m-%d'),
                    'total_tasks': 0,
                    'checked_count': 0
                }
            
            self.logger.info(f"开始检查昨日任务 ({yesterday.strftime('%Y-%m-%d')}) - 总计 {len(yesterday_tasks)} 个任务")
            
            results = {
                'date': yesterday.strftime('%Y-%m-%d'),
                'total_tasks': len(yesterday_tasks),
                'checked_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'downloaded_count': 0,
                'completed_tasks': [],
                'failed_tasks': [],
                'downloaded_tasks': []
            }
            
            for task_id, task_info in yesterday_tasks.items():
                # 模拟人类行为间隔
                self._simulate_human_delay()
                
                # 检查任务状态
                status_result = self.task_manager.check_task_status(task_id)
                results['checked_count'] += 1
                
                if status_result['success']:
                    status = status_result['status']
                    
                    if status == Constants.TaskStatus.COMPLETED:
                        results['completed_count'] += 1
                        results['completed_tasks'].append(task_id)
                        
                        # 检查是否已下载
                        if 'video_path' not in task_info:
                            download_result = self.task_manager.download_completed_video(task_id)
                            if download_result['success']:
                                results['downloaded_count'] += 1
                                results['downloaded_tasks'].append(task_id)
                                self.logger.info(f"昨日任务视频下载成功: {task_id}")
                        else:
                            self.logger.debug(f"昨日任务视频已存在: {task_id}")
                            
                    elif status == Constants.TaskStatus.FAILED:
                        results['failed_count'] += 1
                        results['failed_tasks'].append(task_id)
                        self.logger.warning(f"昨日任务失败: {task_id}")
            
            self.logger.info(f"昨日任务检查完成 - 总计: {results['total_tasks']}, "
                           f"完成: {results['completed_count']}, "
                           f"失败: {results['failed_count']}, "
                           f"新下载: {results['downloaded_count']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"昨日任务检查异常: {str(e)}")
            return {
                'error': str(e),
                'total_tasks': 0
            }
    
    def start_continuous_monitoring(self, check_interval: int = 300) -> None:
        """开始连续监控"""
        self.is_running = True
        self.logger.info(f"开始连续任务监控，检查间隔: {check_interval} 秒")
        
        try:
            while self.is_running:
                self.logger.debug("执行定期状态检查")
                self.check_all_pending_tasks()
                
                # 等待下次检查
                for _ in range(check_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            self.logger.info("监控被用户中断")
        except Exception as e:
            self.logger.error(f"连续监控异常: {str(e)}")
        finally:
            self.is_running = False
            self.logger.info("任务监控已停止")
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_running = False
        self.logger.info("正在停止任务监控...")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            'is_running': self.is_running,
            'start_time': getattr(self, 'start_time', None),
            'checked_tasks_count': getattr(self, 'total_checked', 0)
        }
    
    def _auto_download_video(self, task_id: str) -> bool:
        """自动下载完成的视频"""
        try:
            download_result = self.task_manager.download_completed_video(task_id)
            if download_result['success']:
                self.logger.info(f"自动下载视频成功: {task_id}")
                return True
            else:
                self.logger.error(f"自动下载视频失败: {task_id} - {download_result['error']}")
                return False
        except Exception as e:
            self.logger.error(f"自动下载视频异常: {task_id} - {str(e)}")
            return False
    
    def check_history_tasks_batch(self, max_pages: int = 5) -> Dict[str, Any]:
        """批量历史任务检查 - 新的监控策略"""
        try:
            self.logger.info("开始执行批量历史任务检查")
            
            # 1. 获取历史任务数据
            history_result = self.task_manager.get_tasks_history_batch(
                page=0, 
                page_size=20, 
                max_pages=max_pages
            )
            
            if not history_result['success']:
                return {
                    'success': False,
                    'error': f"获取历史任务失败: {history_result['error']}"
                }
            
            remote_tasks = history_result['tasks']
            
            # 2. 匹配本地任务与远程任务
            match_result = self.task_manager.match_local_tasks_with_remote(remote_tasks)
            
            if not match_result['success']:
                return {
                    'success': False,
                    'error': f"任务匹配失败: {match_result['error']}"
                }
            
            # 3. 下载可下载的视频
            downloadable_tasks = match_result.get('downloadable_tasks', [])
            download_result = {'successful_downloads': 0, 'failed_downloads': 0}
            
            if downloadable_tasks:
                self.logger.info(f"发现 {len(downloadable_tasks)} 个可下载的视频任务")
                download_result = self.task_manager.download_videos_from_history(downloadable_tasks)
            else:
                self.logger.info("没有发现新的可下载视频")
            
            # 4. 汇总结果
            result = {
                'success': True,
                'history_tasks_fetched': history_result['total_tasks'],
                'pages_fetched': history_result['pages_fetched'],
                'local_tasks_count': match_result['local_tasks_count'],
                'remote_tasks_count': match_result['remote_tasks_count'],
                'matched_count': match_result['matched_count'],
                'completed_count': match_result['completed_count'],
                'downloadable_count': match_result['downloadable_count'],
                'successful_downloads': download_result.get('successful_downloads', 0),
                'failed_downloads': download_result.get('failed_downloads', 0),
                'download_details': download_result.get('download_details', []),
                'unmatched_local': list(match_result.get('unmatched_local', [])),
                'unmatched_remote': list(match_result.get('unmatched_remote', []))
            }
            
            self.logger.info(f"批量历史检查完成 - 获取历史任务: {result['history_tasks_fetched']}, "
                           f"匹配任务: {result['matched_count']}, "
                           f"完成任务: {result['completed_count']}, "
                           f"成功下载: {result['successful_downloads']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"批量历史任务检查异常: {str(e)}")
            return {
                'success': False,
                'error': f'批量历史任务检查异常: {str(e)}'
            }

    def download_pending_videos(self) -> Dict[str, Any]:
        """下载待处理视频 - 独立的视频下载方法"""
        try:
            self.logger.info("开始检查并下载待处理视频")
            
            # 获取历史任务（只获取前几页最新的）
            history_result = self.task_manager.get_tasks_history_batch(
                page=0, 
                page_size=20, 
                max_pages=2
            )
            
            if not history_result['success']:
                return {
                    'success': False,
                    'error': f"获取历史任务失败: {history_result['error']}"
                }
            
            # 解析历史任务数据
            parsed_result = self.task_manager._parse_history_response({
                'total': history_result['total_tasks'],
                'tasks': history_result['tasks']
            })
            
            if not parsed_result['success']:
                return {
                    'success': False,
                    'error': f"解析历史任务失败: {parsed_result['error']}"
                }
            
            downloadable_tasks = parsed_result['downloadable_tasks']
            
            if not downloadable_tasks:
                self.logger.info("没有发现可下载的视频")
                return {
                    'success': True,
                    'downloadable_count': 0,
                    'successful_downloads': 0,
                    'failed_downloads': 0
                }
            
            # 过滤出需要下载的任务（检查本地是否已存在）
            tasks_to_download = []
            for task_info in downloadable_tasks:
                task_id = task_info['task_id']
                
                # 检查任务是否在本地记录中以及是否已下载
                local_task_records = self.task_manager.get_task_ids_from_file()
                local_task_ids = {record['task_id'] for record in local_task_records}
                
                if task_id in local_task_ids:
                    # 检查是否已下载
                    task_data = self.task_manager.get_task_info(task_id)
                    if not task_data or 'video_path' not in task_data:
                        tasks_to_download.append(task_info)
            
            if not tasks_to_download:
                self.logger.info("所有匹配的视频都已下载")
                return {
                    'success': True,
                    'downloadable_count': len(downloadable_tasks),
                    'successful_downloads': 0,
                    'failed_downloads': 0,
                    'message': '所有视频都已下载'
                }
            
            # 下载视频
            download_result = self.task_manager.download_videos_from_history(tasks_to_download)
            
            return {
                'success': download_result['success'],
                'downloadable_count': len(downloadable_tasks),
                'tasks_to_download': len(tasks_to_download),
                'successful_downloads': download_result.get('successful_downloads', 0),
                'failed_downloads': download_result.get('failed_downloads', 0),
                'download_details': download_result.get('download_details', []),
                'errors': download_result.get('errors', [])
            }
            
        except Exception as e:
            self.logger.error(f"下载待处理视频异常: {str(e)}")
            return {
                'success': False,
                'error': f'下载待处理视频异常: {str(e)}'
            }

    def _process_completed_task_from_history(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理历史任务中的已完成项"""
        try:
            task_id = task_data.get('id')
            if not task_id:
                return {
                    'success': False,
                    'error': '任务缺少ID'
                }
            
            # 检查任务状态
            if task_data.get('state') != 'success':
                return {
                    'success': False,
                    'error': f'任务 {task_id} 状态不是成功: {task_data.get("state")}'
                }
            
            # 处理创建的内容（视频）
            creations = task_data.get('creations', [])
            if not creations:
                return {
                    'success': False,
                    'error': f'任务 {task_id} 没有创建内容'
                }
            
            processed_creations = []
            download_urls = []
            
            for creation in creations:
                creation_info = {
                    'creation_id': creation.get('id'),
                    'type': creation.get('type', 'video'),
                    'grade': creation.get('grade', 'draft'),
                    'duration': creation.get('duration', 0),
                    'resolution': creation.get('resolution', {}),
                    'has_audio': creation.get('has_audio', False),
                    'created_at': creation.get('created_at', ''),
                    'urls': {}
                }
                
                # 收集所有可用的下载链接
                if creation.get('download_uri'):
                    creation_info['urls']['download'] = creation['download_uri']
                    download_urls.append(creation['download_uri'])
                
                if creation.get('nomark_uri'):
                    creation_info['urls']['nomark'] = creation['nomark_uri']
                    download_urls.append(creation['nomark_uri'])
                
                if creation.get('uri'):
                    creation_info['urls']['watermarked'] = creation['uri']
                
                if creation.get('cover_uri'):
                    creation_info['urls']['cover'] = creation['cover_uri']
                
                processed_creations.append(creation_info)
            
            # 更新本地任务记录
            try:
                if task_id in self.task_manager.tasks:
                    # 更新现有任务记录
                    self.task_manager.tasks[task_id].update({
                        'status': 'completed',
                        'state': 'success',
                        'completed_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'creations_count': len(processed_creations),
                        'download_urls': download_urls,
                        'history_data': task_data  # 保存完整的历史数据
                    })
                else:
                    # 创建新的任务记录
                    self.task_manager.tasks[task_id] = {
                        'task_id': task_id,
                        'status': 'completed',
                        'state': 'success',
                        'type': task_data.get('type', ''),
                        'created_at': task_data.get('created_at', ''),
                        'completed_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'creations_count': len(processed_creations),
                        'download_urls': download_urls,
                        'history_data': task_data
                    }
                
                self.task_manager._save_tasks()
                
            except Exception as e:
                self.logger.warning(f"更新任务 {task_id} 的本地记录时出错: {str(e)}")
            
            result = {
                'success': True,
                'task_id': task_id,
                'task_type': task_data.get('type', ''),
                'created_at': task_data.get('created_at', ''),
                'creations_count': len(processed_creations),
                'download_urls_count': len(download_urls),
                'processed_creations': processed_creations,
                'primary_download_url': download_urls[0] if download_urls else None
            }
            
            self.logger.info(f"已完成任务 {task_id} 处理完成，发现 {len(download_urls)} 个下载链接")
            
            return result
            
        except Exception as e:
            self.logger.error(f"处理已完成任务异常: {str(e)}")
            return {
                'success': False,
                'error': f'处理已完成任务异常: {str(e)}'
            }

    def _simulate_human_delay(self) -> None:
        """模拟人类操作延时"""
        import random
        
        min_delay = self.behavior_config.min_delay
        max_delay = min(self.behavior_config.max_delay, 60)  # 状态检查的延时不超过60秒
        
        # 状态检查使用较短的延时
        delay = random.uniform(min_delay // 3, max_delay // 3)
        time.sleep(delay)
    
    def generate_status_report(self) -> Dict[str, Any]:
        """生成状态报告"""
        try:
            all_tasks = self.task_manager.get_all_tasks()
            
            if not all_tasks:
                return {
                    'total_tasks': 0,
                    'summary': '暂无任务记录'
                }
            
            # 统计各状态任务数量
            status_counts = {
                Constants.TaskStatus.PENDING: 0,
                Constants.TaskStatus.PROCESSING: 0,
                Constants.TaskStatus.COMPLETED: 0,
                Constants.TaskStatus.FAILED: 0,
                Constants.TaskStatus.CANCELLED: 0
            }
            
            recent_tasks = self.task_manager.get_recent_tasks(7)  # 最近7天
            today_tasks = self.task_manager.get_recent_tasks(1)   # 今天
            
            for task_info in all_tasks.values():
                status = task_info.get('status', Constants.TaskStatus.PENDING)
                if status in status_counts:
                    status_counts[status] += 1
            
            # 计算完成率
            total_finished = status_counts[Constants.TaskStatus.COMPLETED] + status_counts[Constants.TaskStatus.FAILED]
            completion_rate = (status_counts[Constants.TaskStatus.COMPLETED] / total_finished * 100) if total_finished > 0 else 0
            
            report = {
                'total_tasks': len(all_tasks),
                'recent_tasks_7d': len(recent_tasks),
                'today_tasks': len(today_tasks),
                'status_counts': status_counts,
                'completion_rate': round(completion_rate, 2),
                'report_time': datetime.now().isoformat(),
                'summary': f"总任务数: {len(all_tasks)}, 完成率: {completion_rate:.1f}%"
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成状态报告异常: {str(e)}")
            return {
                'error': str(e),
                'total_tasks': 0
            }
