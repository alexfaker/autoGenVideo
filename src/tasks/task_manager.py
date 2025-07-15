"""
任务管理器 - 处理视频生成任务的创建、管理和监控
"""

import time
import json
import csv
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from src.config.constants import Constants
from src.utils.logger import get_logger

class TaskManager:
    """视频生成任务管理器"""
    
    def __init__(self, request_handler, file_manager, storage_paths):
        self.request_handler = request_handler
        self.file_manager = file_manager
        self.storage_paths = storage_paths
        self.logger = get_logger("TASK_MANAGER")
        
        # 任务存储文件
        self.tasks_file = storage_paths['cache'] / 'tasks.json'
        self.tasks = self._load_tasks()
        
        # 任务ID记录文件
        self.task_ids_file = storage_paths['cache'] / 'task_ids.csv'
    
    def create_video_task(self, image_path: str, prompt: str, use_off_peak: bool = True) -> Dict[str, Any]:
        """创建视频生成任务"""
        try:
            self.logger.info(f"创建视频生成任务 - 图片: {image_path}, 提示词: {prompt}")
            
            # 1. 上传图片
            upload_result = self.file_manager.upload_image(image_path)
            if not upload_result['success']:
                return {
                    'success': False,
                    'error': f"图片上传失败: {upload_result['error']}"
                }
            
            # 记录图片上传成功的URL，方便测试追踪
            self.logger.info("=" * 60)
            self.logger.info(f"✅ 任务管理器 | 图片上传成功")
            self.logger.info(f"🔗 图片URL: {upload_result['image_url']}")
            self.logger.info(f"📁 本地路径: {image_path}")
            self.logger.info("=" * 60)
            
            # 2. 检查错峰模式状态
            if use_off_peak:
                off_peak_status = self._check_off_peak_status()
                if not off_peak_status['is_available']:
                    self.logger.warning("当前非错峰时段，任务将排队等待")
            
            # 3. 创建任务
            task_data = {
                'image_url': upload_result['image_url'],
                'image_id': upload_result.get('image_id'),
                'ssupload_id': upload_result.get('ssupload_id'),
                'image_width': upload_result.get('image_width'),
                'image_height': upload_result.get('image_height'),
                'prompt': prompt,
                'use_off_peak': use_off_peak,
                'style': 'general',    # 默认风格（改为general以匹配真实API）
                'duration': 5,         # 默认5秒（匹配真实API）
                'quality': 'high'      # 默认高质量
            }
            
            create_result = self._submit_task(task_data)
            if not create_result['success']:
                return create_result
            
            # 4. 保存任务信息
            task_info = {
                'task_id': create_result['task_id'],
                'image_path': image_path,
                'image_url': upload_result['image_url'],
                'prompt': prompt,
                'use_off_peak': use_off_peak,
                'status': Constants.TaskStatus.PENDING,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'api_response': create_result.get('api_response', {})
            }
            
            self.tasks[create_result['task_id']] = task_info
            self._save_tasks()
            
            # 记录任务ID到指定文件，方便后续查看
            self._save_task_id_record(create_result['task_id'], task_info)
            
            self.logger.info(f"任务创建成功 - Task ID: {create_result['task_id']}")
            
            return {
                'success': True,
                'task_id': create_result['task_id'],
                'task_info': task_info,
                'message': '任务创建成功'
            }
            
        except Exception as e:
            self.logger.error(f"创建任务异常: {str(e)}")
            return {
                'success': False,
                'error': f'任务创建异常: {str(e)}'
            }
    
    def _submit_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """提交任务到vidu平台 - 按照真实API格式"""
        try:
            # 构建复杂的任务提交数据，按照真实API格式
            prompt_text = f"[@图1]{task_data['prompt']}"
            
            # 构建prompts数组
            prompts = [
                {
                    "type": "text",
                    "content": prompt_text
                },
                {
                    "type": "image", 
                    "content": task_data['ssupload_id'],
                    "src_imgs": [task_data['ssupload_id']],
                    "selected_region": {
                        "top_left": {"x": 0, "y": 0},
                        "bottom_right": {
                            "x": task_data.get('image_width', 720),
                            "y": task_data.get('image_height', 1122)
                        }
                    },
                    "name": "图1"
                }
            ]
            
            # 计算 aspect_ratio
            aspect_ratio = self.get_aspect_ratio_string(
                task_data.get('image_width'),
                task_data.get('image_height')
            )
            # 构建请求payload
            payload = {
                "input": {
                    "prompts": prompts,
                    "editor_mode": "normal",
                    "enhance": True
                },
                "type": "character2video",
                "settings": {
                    "style": task_data.get('style', 'general'),
                    "duration": task_data.get('duration', 5),
                    "resolution": "1080p",
                    "movement_amplitude": "auto",
                    "aspect_ratio": aspect_ratio,  # 自动判定
                    "sample_count": 1,
                    "schedule_mode": "nopeak" if task_data.get('use_off_peak', True) else "normal",
                    "model_version": "3.0",
                    "use_trial": False
                }
            }
            
            # 构建完整的浏览器模拟请求头
            headers = {
                'accept': '*/*',
                'accept-language': 'zh',
                'content-type': 'application/json',
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
                'x-platform': 'web',
                'x-request-id': f"task-request-{int(time.time() * 1000)}"
            }
            
            self.logger.info(f"提交任务到vidu平台: {prompt_text}")
            
            # 提交任务
            response = self.request_handler.post(
                Constants.APIEndpoints.CREATE_TASK,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                task_response = response.json()
                task_id = task_response.get('id')  # 注意：真实API返回的是'id'不是'task_id'
                
                if not task_id:
                    raise ValueError("任务创建响应中缺少任务ID")
                
                self.logger.info(f"任务创建成功 - Task ID: {task_id}")
                return {
                    'success': True,
                    'task_id': task_id,
                    'api_response': task_response
                }
            else:
                error_msg = f"任务提交失败，状态码: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', error_msg)
                    except:
                        pass
                
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            self.logger.error(f"任务提交异常: {str(e)}")
            return {
                'success': False,
                'error': f'任务提交异常: {str(e)}'
            }
    
    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """检查任务状态 - 按照真实API格式"""
        try:
            # 构建查询参数和请求头
            params = {'id': task_id}
            headers = {
                'accept': '*/*',
                'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
                'origin': 'https://www.vidu.cn',
                'priority': 'u=1, i',
                'referer': 'https://www.vidu.cn/',
                'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
            }
            
            self.logger.info(f"查询任务状态: {task_id}")
            
            # 发起状态查询请求
            response = self.request_handler.get(
                Constants.APIEndpoints.TASK_STATUS,
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                status_data = response.json()
                
                # 映射API返回的state到内部状态
                api_state = status_data.get('state', '')
                internal_status = self._map_api_state_to_internal_status(api_state)
                
                # 计算进度（根据estimated_time_left推算）
                estimated_time_left = status_data.get('estimated_time_left', 0)
                progress = 100 if api_state == 'success' else (90 if estimated_time_left == 0 else 50)
                
                # 更新本地任务信息
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = internal_status
                    self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
                    self.tasks[task_id]['progress'] = progress
                    self.tasks[task_id]['api_state'] = api_state
                    self.tasks[task_id]['estimated_time_left'] = estimated_time_left
                    
                    if internal_status == Constants.TaskStatus.COMPLETED:
                        self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                    
                    self._save_tasks()
                
                self.logger.info(f"任务 {task_id} 状态: {api_state} -> {internal_status}")
                
                return {
                    'success': True,
                    'task_id': task_id,
                    'status': internal_status,
                    'api_state': api_state,
                    'progress': progress,
                    'estimated_time_left': estimated_time_left,
                    'err_code': status_data.get('err_code', ''),
                    'queue_wait_time': status_data.get('queue_wait_time', {}),
                    'api_response': status_data
                }
            else:
                error_msg = f"状态查询失败，状态码: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', error_msg)
                    except:
                        pass
                
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            self.logger.error(f"状态查询异常: {str(e)}")
            return {
                'success': False,
                'error': f'状态查询异常: {str(e)}'
            }
    
    def _map_api_state_to_internal_status(self, api_state: str) -> str:
        """映射API返回的state值到内部状态常量"""
        state_mapping = {
            'success': Constants.TaskStatus.COMPLETED,
            'completed': Constants.TaskStatus.COMPLETED,
            'processing': Constants.TaskStatus.PROCESSING,
            'pending': Constants.TaskStatus.PENDING,
            'waiting': Constants.TaskStatus.PENDING,
            'queued': Constants.TaskStatus.PENDING,
            'failed': Constants.TaskStatus.FAILED,
            'error': Constants.TaskStatus.FAILED,
            'cancelled': Constants.TaskStatus.CANCELLED,
            'canceled': Constants.TaskStatus.CANCELLED
        }
        
        return state_mapping.get(api_state.lower(), Constants.TaskStatus.PENDING)
    
    def download_completed_video(self, task_id: str) -> Dict[str, Any]:
        """下载已完成的视频"""
        try:
            if task_id not in self.tasks:
                return {
                    'success': False,
                    'error': '任务不存在'
                }
            
            task_info = self.tasks[task_id]
            
            if task_info['status'] != Constants.TaskStatus.COMPLETED:
                return {
                    'success': False,
                    'error': '任务尚未完成'
                }
            
            if 'video_url' not in task_info:
                # 注意：新的状态查询API不返回video_url，需要使用其他API获取
                self.logger.warning(f"任务 {task_id} 缺少视频下载链接，可能需要使用任务结果API获取")
                return {
                    'success': False,
                    'error': '视频下载链接不可用，任务可能使用了新的API格式'
                }
            
            # 下载视频
            download_result = self.file_manager.download_video(
                task_info['video_url'],
                task_id,
                f"video_{task_id}.mp4"
            )
            
            if download_result['success']:
                # 更新任务信息
                task_info['downloaded_at'] = datetime.now().isoformat()
                task_info['video_path'] = download_result['video_path']
                self._save_tasks()
                
                self.logger.info(f"视频下载成功 - Task ID: {task_id}")
            
            return download_result
            
        except Exception as e:
            self.logger.error(f"视频下载异常: {str(e)}")
            return {
                'success': False,
                'error': f'下载异常: {str(e)}'
            }

    def get_tasks_history_batch(self, page: int = 0, page_size: int = 20, max_pages: int = 10) -> Dict[str, Any]:
        """批量获取历史任务 - 支持分页获取"""
        try:
            all_tasks = []
            total_fetched = 0
            current_page = page
            
            self.logger.info(f"开始批量获取历史任务，起始页: {page}")
            
            while current_page < max_pages:
                # 构建查询参数
                params = {
                    'pager.page': current_page,
                    'pager.pagesz': page_size,
                    'scenes': '',  # 空字符串表示所有场景
                }
                
                # 添加所有支持的任务类型
                for task_type in Constants.HistoryTasksConfig.TASK_TYPES:
                    params[f'types'] = task_type  # 注意：这样会覆盖，需要用特殊处理
                
                # 特殊处理多个types参数 - 构建URL参数字符串
                types_params = '&'.join([f'types={task_type}' for task_type in Constants.HistoryTasksConfig.TASK_TYPES])
                base_params = f"pager.page={current_page}&pager.pagesz={page_size}&scenes="
                full_params_str = f"{base_params}&{types_params}"
                
                self.logger.info(f"获取第 {current_page + 1} 页历史任务")
                
                # 发起请求
                url = f"{Constants.APIEndpoints.TASKS_HISTORY_ME}?{full_params_str}"
                response = self.request_handler.get(
                    url,
                    headers=Constants.HistoryTasksConfig.DEFAULT_HEADERS
                )
                
                if response.status_code == 200:
                    history_data = response.json()
                    
                    # 解析响应数据
                    page_tasks = history_data.get('tasks', [])
                    total_count = history_data.get('total', 0)
                    
                    if not page_tasks:
                        self.logger.info("当前页无任务数据，停止分页查询")
                        break
                    
                    all_tasks.extend(page_tasks)
                    total_fetched += len(page_tasks)
                    
                    self.logger.info(f"第 {current_page + 1} 页获取到 {len(page_tasks)} 个任务")
                    
                    # 检查是否还有更多页
                    if len(page_tasks) < page_size or total_fetched >= total_count:
                        self.logger.info("已获取所有可用的历史任务")
                        break
                        
                else:
                    error_msg = f"历史任务查询失败，状态码: {response.status_code}"
                    if response.text:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('message', error_msg)
                        except:
                            pass
                    
                    self.logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'status_code': response.status_code
                    }
                
                current_page += 1
            
            self.logger.info(f"批量历史任务获取完成，共获取 {total_fetched} 个任务")
            
            return {
                'success': True,
                'total_tasks': total_fetched,
                'tasks': all_tasks,
                'pages_fetched': current_page - page
            }
            
        except Exception as e:
            self.logger.error(f"批量获取历史任务异常: {str(e)}")
            return {
                'success': False,
                'error': f'批量获取历史任务异常: {str(e)}'
            }
    
    def match_local_tasks_with_remote(self, remote_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """匹配本地任务ID与远程历史任务"""
        try:
            # 获取本地任务ID记录
            local_task_records = self.get_task_ids_from_file()
            local_task_ids = {record['task_id'] for record in local_task_records if record.get('task_id')}
            
            # 创建远程任务字典 (task_id -> task_data)
            remote_task_dict = {task['id']: task for task in remote_tasks}
            remote_task_ids = set(remote_task_dict.keys())
            
            # 找到匹配的任务ID
            matched_task_ids = local_task_ids.intersection(remote_task_ids)
            
            # 分类匹配结果
            matched_tasks = []
            completed_tasks = []
            downloadable_tasks = []
            
            for task_id in matched_task_ids:
                remote_task = remote_task_dict[task_id]
                task_state = remote_task.get('state', '')
                
                matched_task_info = {
                    'task_id': task_id,
                    'state': task_state,
                    'remote_data': remote_task
                }
                
                matched_tasks.append(matched_task_info)
                
                # 检查是否为已完成任务
                if task_state == 'success':
                    completed_tasks.append(matched_task_info)
                    
                    # 检查是否有可下载的视频
                    creations = remote_task.get('creations', [])
                    for creation in creations:
                        if creation.get('download_uri') or creation.get('nomark_uri'):
                            downloadable_tasks.append({
                                **matched_task_info,
                                'creation': creation
                            })
                            break  # 找到第一个可下载的creation即可
            
            result = {
                'success': True,
                'local_tasks_count': len(local_task_ids),
                'remote_tasks_count': len(remote_task_ids),
                'matched_count': len(matched_task_ids),
                'completed_count': len(completed_tasks),
                'downloadable_count': len(downloadable_tasks),
                'matched_tasks': matched_tasks,
                'completed_tasks': completed_tasks,
                'downloadable_tasks': downloadable_tasks,
                'unmatched_local': local_task_ids - remote_task_ids,
                'unmatched_remote': remote_task_ids - local_task_ids
            }
            
            self.logger.info(f"任务匹配完成 - 本地: {len(local_task_ids)}, "
                           f"远程: {len(remote_task_ids)}, "
                           f"匹配: {len(matched_task_ids)}, "
                           f"已完成: {len(completed_tasks)}, "
                           f"可下载: {len(downloadable_tasks)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"任务匹配异常: {str(e)}")
            return {
                'success': False,
                'error': f'任务匹配异常: {str(e)}'
            }

    def download_videos_from_history(self, downloadable_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史任务数据下载视频"""
        try:
            download_results = {
                'success': True,
                'total_tasks': len(downloadable_tasks),
                'successful_downloads': 0,
                'failed_downloads': 0,
                'download_details': [],
                'errors': []
            }
            
            if not downloadable_tasks:
                self.logger.info("没有可下载的视频任务")
                return download_results
            
            self.logger.info(f"开始从历史数据下载 {len(downloadable_tasks)} 个视频")
            
            for task_info in downloadable_tasks:
                task_id = task_info['task_id']
                creation = task_info['creation']
                
                try:
                    # 检查是否已经下载过
                    if task_id in self.tasks and 'video_path' in self.tasks[task_id]:
                        self.logger.info(f"任务 {task_id} 的视频已存在，跳过下载")
                        download_results['download_details'].append({
                            'task_id': task_id,
                            'status': 'skipped',
                            'reason': '视频已存在'
                        })
                        continue
                    
                    # 优先使用无水印下载链接
                    download_url = creation.get('nomark_uri') or creation.get('download_uri')
                    if not download_url:
                        error_msg = f"任务 {task_id} 没有有效的下载链接"
                        self.logger.warning(error_msg)
                        download_results['failed_downloads'] += 1
                        download_results['errors'].append(error_msg)
                        download_results['download_details'].append({
                            'task_id': task_id,
                            'status': 'failed',
                            'reason': '缺少下载链接'
                        })
                        continue
                    
                    # 生成文件名
                    creation_id = creation.get('id', task_id)
                    filename = f"vidu-video-{creation_id}.mp4"
                    
                    self.logger.info(f"下载任务 {task_id} 的视频: {filename}")
                    
                    # 调用文件管理器下载视频
                    download_result = self.file_manager.download_video(
                        download_url,
                        task_id,
                        filename
                    )
                    
                    if download_result['success']:
                        # 更新本地任务信息
                        if task_id not in self.tasks:
                            # 如果本地任务记录不存在，创建基本记录
                            self.tasks[task_id] = {
                                'task_id': task_id,
                                'status': Constants.TaskStatus.COMPLETED,
                                'created_at': task_info['remote_data'].get('created_at', ''),
                                'updated_at': datetime.now().isoformat()
                            }
                        
                        # 更新下载信息
                        self.tasks[task_id].update({
                            'video_path': download_result['video_path'],
                            'video_url': download_url,
                            'downloaded_at': datetime.now().isoformat(),
                            'file_size': download_result.get('file_size', 0),
                            'creation_id': creation_id,
                            'status': Constants.TaskStatus.COMPLETED
                        })
                        
                        self._save_tasks()
                        
                        download_results['successful_downloads'] += 1
                        download_results['download_details'].append({
                            'task_id': task_id,
                            'status': 'success',
                            'video_path': download_result['video_path'],
                            'file_size': download_result.get('file_size', 0)
                        })
                        
                        self.logger.info(f"任务 {task_id} 视频下载成功: {download_result['video_path']}")
                        
                    else:
                        error_msg = f"任务 {task_id} 视频下载失败: {download_result['error']}"
                        self.logger.error(error_msg)
                        download_results['failed_downloads'] += 1
                        download_results['errors'].append(error_msg)
                        download_results['download_details'].append({
                            'task_id': task_id,
                            'status': 'failed',
                            'reason': download_result['error']
                        })
                
                except Exception as e:
                    error_msg = f"处理任务 {task_id} 下载时发生异常: {str(e)}"
                    self.logger.error(error_msg)
                    download_results['failed_downloads'] += 1
                    download_results['errors'].append(error_msg)
                    download_results['download_details'].append({
                        'task_id': task_id,
                        'status': 'failed',
                        'reason': f'异常: {str(e)}'
                    })
            
            # 设置整体成功状态
            download_results['success'] = download_results['failed_downloads'] == 0
            
            self.logger.info(f"历史视频下载完成 - 成功: {download_results['successful_downloads']}, "
                           f"失败: {download_results['failed_downloads']}")
            
            return download_results
            
        except Exception as e:
            self.logger.error(f"历史视频下载异常: {str(e)}")
            return {
                'success': False,
                'error': f'历史视频下载异常: {str(e)}'
            }

    def _parse_history_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析批量历史任务接口返回数据"""
        try:
            parsed_result = {
                'success': True,
                'total': response_data.get('total', 0),
                'tasks': [],
                'completed_tasks': [],
                'downloadable_tasks': [],
                'task_states': {},
                'parse_errors': []
            }
            
            raw_tasks = response_data.get('tasks', [])
            
            for task in raw_tasks:
                try:
                    task_id = task.get('id')
                    if not task_id:
                        parsed_result['parse_errors'].append("任务缺少ID字段")
                        continue
                    
                    # 基本任务信息
                    parsed_task = {
                        'id': task_id,
                        'state': task.get('state', ''),
                        'type': task.get('type', ''),
                        'scene': task.get('scene', ''),
                        'created_at': task.get('created_at', ''),
                        'err_code': task.get('err_code', ''),
                        'input': task.get('input', {}),
                        'settings': task.get('settings', {}),
                        'creations': task.get('creations', [])
                    }
                    
                    parsed_result['tasks'].append(parsed_task)
                    
                    # 记录任务状态
                    parsed_result['task_states'][task_id] = parsed_task['state']
                    
                    # 检查是否为已完成任务
                    if parsed_task['state'] == 'success':
                        parsed_result['completed_tasks'].append(parsed_task)
                        
                        # 检查是否有可下载的视频
                        for creation in parsed_task['creations']:
                            if (creation.get('download_uri') or 
                                creation.get('nomark_uri') or 
                                creation.get('uri')):
                                
                                downloadable_info = {
                                    'task_id': task_id,
                                    'task_data': parsed_task,
                                    'creation': creation,
                                    'download_url': (creation.get('nomark_uri') or 
                                                   creation.get('download_uri') or 
                                                   creation.get('uri')),
                                    'creation_id': creation.get('id'),
                                    'video_duration': creation.get('duration', 0),
                                    'resolution': creation.get('resolution', {}),
                                    'file_type': creation.get('type', 'video')
                                }
                                
                                parsed_result['downloadable_tasks'].append(downloadable_info)
                                
                except Exception as e:
                    error_msg = f"解析单个任务时出错: {str(e)}"
                    parsed_result['parse_errors'].append(error_msg)
                    self.logger.warning(error_msg)
            
            self.logger.info(f"历史任务数据解析完成 - 总数: {parsed_result['total']}, "
                           f"解析成功: {len(parsed_result['tasks'])}, "
                           f"已完成: {len(parsed_result['completed_tasks'])}, "
                           f"可下载: {len(parsed_result['downloadable_tasks'])}")
            
            if parsed_result['parse_errors']:
                self.logger.warning(f"解析过程中发现 {len(parsed_result['parse_errors'])} 个错误")
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"解析历史任务响应异常: {str(e)}")
            return {
                'success': False,
                'error': f'解析历史任务响应异常: {str(e)}'
            }

    def batch_create_video_tasks(self, images_dir: str, prompts_file: str, 
                                 use_off_peak: bool = False, task_delay: float = 5.0) -> Dict[str, Any]:
        """批量创建视频生成任务"""
        try:
            self.logger.info(f"开始批量创建视频任务 - 图片目录: {images_dir}, 提示词文件: {prompts_file}")
            
            # 1. 验证输入
            validation_result = self._validate_batch_inputs(images_dir, prompts_file)
            if not validation_result['success']:
                return validation_result
            
            # 2. 扫描和排序图片文件
            images_result = self._scan_and_sort_images(images_dir)
            if not images_result['success']:
                return images_result
            
            image_files = images_result['image_files']
            
            # 3. 加载提示词
            prompts_result = self._load_prompts_from_file(prompts_file)
            if not prompts_result['success']:
                return prompts_result
            
            prompts = prompts_result['prompts']
            
            # 4. 检查数量匹配
            if len(image_files) != len(prompts):
                self.logger.warning(f"图片数量({len(image_files)})与提示词数量({len(prompts)})不匹配")
                min_count = min(len(image_files), len(prompts))
                self.logger.info(f"将处理前{min_count}组匹配的图片和提示词")
                image_files = image_files[:min_count]
                prompts = prompts[:min_count]
            
            # 5. 批量创建任务
            batch_results = {
                'success': True,
                'total_tasks': len(image_files),
                'successful_tasks': 0,
                'failed_tasks': 0,
                'task_results': [],
                'created_task_ids': [],
                'errors': []
            }
            
            self.logger.info(f"开始批量创建 {len(image_files)} 个视频任务")
            
            for i, (image_file, prompt) in enumerate(zip(image_files, prompts), 1):
                try:
                    self.logger.info(f"创建第 {i}/{len(image_files)} 个任务")
                    self.logger.info(f"图片: {image_file}")
                    self.logger.info(f"提示词: {prompt[:50]}...")  # 只显示前50个字符
                    
                    # 创建单个任务
                    task_result = self.create_video_task(
                        image_path=image_file,
                        prompt=prompt,
                        use_off_peak=use_off_peak
                    )
                    
                    # 记录结果
                    task_info = {
                        'index': i,
                        'image_file': image_file,
                        'prompt': prompt,
                        'success': task_result['success'],
                        'task_id': task_result.get('task_id', ''),
                        'error': task_result.get('error', '')
                    }
                    
                    batch_results['task_results'].append(task_info)
                    
                    if task_result['success']:
                        batch_results['successful_tasks'] += 1
                        batch_results['created_task_ids'].append(task_result['task_id'])
                        self.logger.info(f"✅ 第 {i} 个任务创建成功: {task_result['task_id']}")
                    else:
                        batch_results['failed_tasks'] += 1
                        error_msg = f"第 {i} 个任务创建失败: {task_result['error']}"
                        batch_results['errors'].append(error_msg)
                        self.logger.error(error_msg)
                    
                    # 任务间延时（最后一个任务不需要延时）
                    if i < len(image_files):
                        self.logger.debug(f"等待 {task_delay} 秒后创建下一个任务...")
                        time.sleep(task_delay)
                
                except Exception as e:
                    error_msg = f"处理第 {i} 个任务时发生异常: {str(e)}"
                    self.logger.error(error_msg)
                    
                    batch_results['failed_tasks'] += 1
                    batch_results['errors'].append(error_msg)
                    batch_results['task_results'].append({
                        'index': i,
                        'image_file': image_file,
                        'prompt': prompt,
                        'success': False,
                        'task_id': '',
                        'error': str(e)
                    })
            
            # 6. 汇总结果
            success_rate = (batch_results['successful_tasks'] / batch_results['total_tasks']) * 100
            batch_results['success_rate'] = success_rate
            
            if batch_results['failed_tasks'] == 0:
                batch_results['success'] = True
                self.logger.info(f"✅ 批量任务创建完成 - 全部成功 ({batch_results['successful_tasks']}/{batch_results['total_tasks']})")
            else:
                batch_results['success'] = batch_results['successful_tasks'] > 0  # 部分成功也算成功
                self.logger.info(f"⚠️ 批量任务创建完成 - 成功: {batch_results['successful_tasks']}, "
                               f"失败: {batch_results['failed_tasks']}, "
                               f"成功率: {success_rate:.1f}%")
            
            return batch_results
            
        except Exception as e:
            self.logger.error(f"批量创建视频任务异常: {str(e)}")
            return {
                'success': False,
                'error': f'批量创建视频任务异常: {str(e)}'
            }

    def _scan_and_sort_images(self, images_dir: str) -> Dict[str, Any]:
        """扫描和自然排序图片文件"""
        try:
            import os
            import re
            from pathlib import Path
            
            images_path = Path(images_dir)
            if not images_path.exists():
                return {
                    'success': False,
                    'error': f'图片目录不存在: {images_dir}'
                }
            
            # 获取所有图片文件
            image_extensions = Constants.FileConstants.SUPPORTED_IMAGE_FORMATS
            image_files = []
            
            for file_path in images_path.iterdir():
                if file_path.is_file():
                    # 检查文件扩展名
                    if any(file_path.name.lower().endswith(ext) for ext in image_extensions):
                        image_files.append(str(file_path.absolute()))
            
            if not image_files:
                return {
                    'success': False,
                    'error': f'在目录 {images_dir} 中未找到支持的图片文件'
                }
            
            # 自然排序（处理数字序号）
            def natural_sort_key(filename):
                """自然排序的键函数，正确处理数字"""
                base_name = os.path.basename(filename)
                # 提取文件名中的数字部分
                parts = re.split(r'(\d+)', base_name)
                # 将数字部分转换为整数，非数字部分保持字符串
                result = []
                for part in parts:
                    if part.isdigit():
                        result.append(int(part))
                    else:
                        result.append(part)
                return result
            
            # 按自然顺序排序
            image_files.sort(key=natural_sort_key)
            
            self.logger.info(f"扫描到 {len(image_files)} 个图片文件")
            for i, image_file in enumerate(image_files, 1):
                self.logger.debug(f"  {i}. {os.path.basename(image_file)}")
            
            return {
                'success': True,
                'image_files': image_files,
                'count': len(image_files)
            }
            
        except Exception as e:
            self.logger.error(f"扫描图片文件异常: {str(e)}")
            return {
                'success': False,
                'error': f'扫描图片文件异常: {str(e)}'
            }

    def _load_prompts_from_file(self, prompts_file: str) -> Dict[str, Any]:
        """从文件加载提示词"""
        try:
            from pathlib import Path
            
            prompts_path = Path(prompts_file)
            if not prompts_path.exists():
                return {
                    'success': False,
                    'error': f'提示词文件不存在: {prompts_file}'
                }
            
            # 读取文件内容
            with open(prompts_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return {
                    'success': False,
                    'error': f'提示词文件为空: {prompts_file}'
                }
            
            # 按行分割提示词
            prompts = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not prompts:
                return {
                    'success': False,
                    'error': f'提示词文件中没有有效内容: {prompts_file}'
                }
            
            self.logger.info(f"从文件加载到 {len(prompts)} 个提示词")
            for i, prompt in enumerate(prompts, 1):
                preview = prompt[:30] + '...' if len(prompt) > 30 else prompt
                self.logger.debug(f"  {i}. {preview}")
            
            return {
                'success': True,
                'prompts': prompts,
                'count': len(prompts)
            }
            
        except Exception as e:
            self.logger.error(f"加载提示词文件异常: {str(e)}")
            return {
                'success': False,
                'error': f'加载提示词文件异常: {str(e)}'
            }

    def _validate_batch_inputs(self, images_dir: str, prompts_file: str) -> Dict[str, Any]:
        """验证批量输入的有效性"""
        try:
            from pathlib import Path
            
            # 检查图片目录
            images_path = Path(images_dir)
            if not images_path.exists():
                return {
                    'success': False,
                    'error': f'图片目录不存在: {images_dir}'
                }
            
            if not images_path.is_dir():
                return {
                    'success': False,
                    'error': f'指定的路径不是目录: {images_dir}'
                }
            
            # 检查提示词文件
            prompts_path = Path(prompts_file)
            if not prompts_path.exists():
                return {
                    'success': False,
                    'error': f'提示词文件不存在: {prompts_file}'
                }
            
            if not prompts_path.is_file():
                return {
                    'success': False,
                    'error': f'指定的路径不是文件: {prompts_file}'
                }
            
            # 检查文件可读性
            try:
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    f.read(1)  # 尝试读取一个字符
            except Exception as e:
                return {
                    'success': False,
                    'error': f'无法读取提示词文件: {str(e)}'
                }
            
            self.logger.info(f"输入验证通过 - 图片目录: {images_dir}, 提示词文件: {prompts_file}")
            
            return {
                'success': True,
                'images_dir': str(images_path.absolute()),
                'prompts_file': str(prompts_path.absolute())
            }
            
        except Exception as e:
            self.logger.error(f"验证批量输入异常: {str(e)}")
            return {
                'success': False,
                'error': f'验证批量输入异常: {str(e)}'
            }

    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务"""
        return self.tasks.copy()
    
    def get_tasks_by_status(self, status: str) -> Dict[str, Any]:
        """根据状态获取任务"""
        filtered_tasks = {}
        for task_id, task_info in self.tasks.items():
            if task_info.get('status') == status:
                filtered_tasks[task_id] = task_info
        return filtered_tasks
    
    def get_recent_tasks(self, days: int = 7) -> Dict[str, Any]:
        """获取最近的任务"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_tasks = {}
        
        for task_id, task_info in self.tasks.items():
            created_at = datetime.fromisoformat(task_info['created_at'])
            if created_at >= cutoff_date:
                recent_tasks[task_id] = task_info
        
        return recent_tasks
    
    def _check_off_peak_status(self) -> Dict[str, Any]:
        """检查错峰模式状态"""
        try:
            current_hour = datetime.now().hour
            # 简单的错峰时段判断（后续可以通过API获取）
            off_peak_hours = [0, 1, 2, 3, 4, 5, 6]  # 凌晨0-6点
            
            is_off_peak = current_hour in off_peak_hours
            
            return {
                'is_available': is_off_peak,
                'current_hour': current_hour,
                'next_off_peak': self._get_next_off_peak_time()
            }
            
        except Exception as e:
            self.logger.error(f"错峰状态检查异常: {str(e)}")
            return {
                'is_available': False,
                'error': str(e)
            }
    
    def _get_next_off_peak_time(self) -> str:
        """获取下一个错峰时段"""
        current_time = datetime.now()
        next_off_peak = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 如果当前时间已过今日错峰时段，则返回明日0点
        if current_time.hour >= 7:
            next_off_peak += timedelta(days=1)
        
        return next_off_peak.isoformat()
    
    def _load_tasks(self) -> Dict[str, Any]:
        """加载任务数据"""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"加载任务数据失败: {str(e)}")
        
        return {}
    
    def _save_tasks(self) -> None:
        """保存任务数据"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存任务数据失败: {str(e)}")
    
    def _save_task_id_record(self, task_id: str, task_info: Dict[str, Any]) -> None:
        """记录任务ID到CSV文件，方便后续查看"""
        try:
            # 检查文件是否存在，如果不存在则创建并写入表头
            file_exists = self.task_ids_file.exists()
            
            with open(self.task_ids_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 如果文件不存在，先写入表头
                if not file_exists:
                    writer.writerow(['task_id', 'created_at', 'prompt', 'image_path', 'status', 'use_off_peak'])
                
                # 写入任务记录
                writer.writerow([
                    task_id,
                    task_info.get('created_at', ''),
                    task_info.get('prompt', ''),
                    task_info.get('image_path', ''),
                    task_info.get('status', ''),
                    task_info.get('use_off_peak', False)
                ])
                
            self.logger.info(f"任务ID记录已保存到文件: {task_id}")
            
        except Exception as e:
            self.logger.error(f"保存任务ID记录失败: {str(e)}")
    
    def get_task_ids_from_file(self) -> List[Dict[str, Any]]:
        """从CSV文件读取所有任务ID记录"""
        try:
            if not self.task_ids_file.exists():
                return []
            
            task_records = []
            with open(self.task_ids_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task_records.append(row)
            
            self.logger.info(f"从文件读取到 {len(task_records)} 个任务ID记录")
            return task_records
            
        except Exception as e:
            self.logger.error(f"读取任务ID记录失败: {str(e)}")
            return []
    
    def show_task_ids_summary(self) -> None:
        """显示任务ID记录摘要信息"""
        try:
            records = self.get_task_ids_from_file()
            
            if not records:
                print("📋 暂无任务ID记录")
                return
            
            print(f"\n📋 任务ID记录摘要 (共 {len(records)} 个任务):")
            print("=" * 80)
            print(f"{'任务ID':<20} {'创建时间':<20} {'状态':<10} {'提示词':<30}")
            print("-" * 80)
            
            for record in records[-10:]:  # 显示最近10个任务
                task_id = record.get('task_id', '')[:18]
                created_at = record.get('created_at', '')[:19]
                status = record.get('status', '')
                prompt = record.get('prompt', '')[:28]
                
                print(f"{task_id:<20} {created_at:<20} {status:<10} {prompt:<30}")
            
            if len(records) > 10:
                print(f"... 还有 {len(records) - 10} 个任务")
            
            print("=" * 80)
            print(f"💡 完整记录文件位置: {self.task_ids_file}")
            
        except Exception as e:
            self.logger.error(f"显示任务ID摘要失败: {str(e)}")
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """清理旧任务记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        tasks_to_remove = []
        for task_id, task_info in self.tasks.items():
            created_at = datetime.fromisoformat(task_info['created_at'])
            if created_at < cutoff_date:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            self._save_tasks()
            self.logger.info(f"清理了 {cleaned_count} 个旧任务记录")
        
        return cleaned_count

    def get_aspect_ratio_string(self, width, height):
        """根据图片宽高自动判定常见比例，返回标准字符串或 W:H 格式"""
        try:
            if not width or not height:
                self.logger.warning("图片宽高缺失，aspect_ratio 默认16:9")
                return "16:9"
            ratio = width / height
            # 常见比例及其标准值
            common_ratios = {
                "16:9": 16/9,
                "9:16": 9/16,
                "1:1": 1.0,
                "4:3": 4/3,
                "3:4": 3/4,
                "21:9": 21/9
            }
            tolerance = 0.01  # 1% 容差
            for k, v in common_ratios.items():
                if abs(ratio - v) < tolerance:
                    return k
            # 未匹配到常见比例，返回原始宽高
            return f"{width}:{height}"
        except Exception as e:
            self.logger.error(f"宽高比判定异常: {str(e)}，aspect_ratio 默认16:9")
            return "16:9"
