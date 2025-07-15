"""
文件管理器 - 处理图片上传、视频下载和文件处理
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import requests
from src.config.constants import Constants
from src.utils.logger import get_logger

class FileManager:
    """文件管理器"""
    
    def __init__(self, request_handler, storage_paths: Dict[str, Path]):
        self.request_handler = request_handler
        self.storage_paths = storage_paths
        self.logger = get_logger("FILE_MANAGER")
        
        # 确保存储目录存在
        for path in storage_paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    def prepare_image(self, image_path: str) -> Dict[str, Any]:
        """预处理图片"""
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                return {
                    'success': False,
                    'error': f'图片文件不存在: {image_path}'
                }
            
            # 验证图片格式
            if image_path.suffix.lower() not in Constants.FileConstants.SUPPORTED_IMAGE_FORMATS:
                return {
                    'success': False,
                    'error': f'不支持的图片格式: {image_path.suffix}'
                }
            
            # 检查文件大小
            file_size = image_path.stat().st_size
            if file_size > Constants.FileConstants.MAX_IMAGE_SIZE:
                return {
                    'success': False,
                    'error': f'图片文件过大: {file_size} bytes'
                }
            
            # 处理图片
            processed_path = self._process_image(image_path)
            
            return {
                'success': True,
                'original_path': str(image_path),
                'processed_path': str(processed_path),
                'file_size': processed_path.stat().st_size,
                'image_hash': self._calculate_file_hash(processed_path)
            }
            
        except Exception as e:
            self.logger.error(f"图片预处理失败: {str(e)}")
            return {
                'success': False,
                'error': f'图片处理异常: {str(e)}'
            }
    
    def upload_image(self, image_path: str) -> Dict[str, Any]:
        """上传图片到vidu平台 - 三步上传流程"""
        try:
            # 预处理图片
            prep_result = self.prepare_image(image_path)
            if not prep_result['success']:
                return prep_result
            
            processed_path = Path(prep_result['processed_path'])
            
            # 获取图片元数据
            metadata = self._get_image_metadata(processed_path)
            self.logger.info(f"开始上传图片: {processed_path.name}, 尺寸: {metadata['width']}x{metadata['height']}")
            
            # 步骤1: 上传元数据
            meta_result = self._upload_metadata(metadata)
            if not meta_result['success']:
                # 清理临时文件
                if processed_path.name.startswith('processed_'):
                    processed_path.unlink()
                return meta_result
            
            upload_id = meta_result['upload_id']
            # // 这个是文件上传后的链接
            put_url = meta_result['put_url']
            
            # 步骤2: 上传二进制数据
            binary_result = self._upload_binary_data(processed_path, put_url, metadata)
            if not binary_result['success']:
                # 清理临时文件
                if processed_path.name.startswith('processed_'):
                    processed_path.unlink()
                return binary_result
            
            etag = binary_result['etag']
            
            # 步骤3: 完成上传
            finish_result = self._finish_upload(upload_id, etag)
            
            # 清理临时文件
            if processed_path.name.startswith('processed_'):
                processed_path.unlink()
            
            if finish_result['success']:
                self.logger.info(f"图片上传成功: {finish_result['file_uri']}")
                
                # 醒目的URL日志记录，方便测试
                self.logger.info("=" * 60)
                self.logger.info(f"📷 测试URL | 图片上传成功")
                self.logger.info(f"🔗 图片URL: {put_url}")
                self.logger.info(f"🆔 上传ID: {upload_id}")
                self.logger.info(f"🔗 ssupload格式: ssupload:?id={upload_id}")
                self.logger.info("=" * 60)
                
                return {
                    'success': True,
                    'image_url': put_url,
                    'image_id': upload_id,
                    'ssupload_id': f"ssupload:?id={upload_id}",
                    'image_width': metadata['width'],
                    'image_height': metadata['height'],
                    'upload_response': finish_result['finish_response']
                }
            else:
                return finish_result
                
        except Exception as e:
            self.logger.error(f"图片上传异常: {str(e)}")
            return {
                'success': False,
                'error': f'上传异常: {str(e)}'
            }
    
    def download_video(self, video_url: str, task_id: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """下载视频文件"""
        try:
            if not filename:
                filename = f"video_{task_id}_{int(time.time())}.mp4"
            
            video_path = self.storage_paths['output'] / filename
            
            self.logger.info(f"开始下载视频: {video_url}")
            
            # 修复点：区分完整URL和相对路径，完整URL直接用requests.get
            # 这样可避免 request_handler.get 拼接 base_url 导致 host 错误
            if video_url.startswith('http://') or video_url.startswith('https://'):
                import requests
                response = requests.get(video_url, stream=True)
            else:
                response = self.request_handler.get(video_url, stream=True)
            
            if response.status_code == 200:
                with open(video_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证下载的文件
                if self._verify_video_file(video_path):
                    self.logger.info(f"视频下载成功: {video_path}")
                    return {
                        'success': True,
                        'video_path': str(video_path),
                        'file_size': video_path.stat().st_size
                    }
                else:
                    video_path.unlink()  # 删除损坏的文件
                    return {
                        'success': False,
                        'error': '下载的视频文件损坏'
                    }
            else:
                return {
                    'success': False,
                    'error': f'视频下载失败，状态码: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.error(f"视频下载异常: {str(e)}")
            return {
                'success': False,
                'error': f'下载异常: {str(e)}'
            }
    
    def _process_image(self, image_path: Path) -> Path:
        """处理图片 - 压缩和格式优化"""
        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 检查分辨率并调整
                max_resolution = Constants.FileConstants.MAX_IMAGE_RESOLUTION
                if img.size[0] > max_resolution[0] or img.size[1] > max_resolution[1]:
                    img.thumbnail(max_resolution, Image.Resampling.LANCZOS)
                    self.logger.info(f"图片已调整大小: {img.size}")
                
                # 保存处理后的图片
                processed_filename = f"processed_{int(time.time())}_{image_path.name}"
                processed_path = self.storage_paths['cache'] / processed_filename
                
                # 保存为JPEG格式以减小文件大小
                img.save(
                    processed_path, 
                    'JPEG', 
                    quality=Constants.FileConstants.DEFAULT_IMAGE_QUALITY,
                    optimize=True
                )
                
                self.logger.info(f"图片处理完成: {processed_path}")
                return processed_path
                
        except Exception as e:
            self.logger.error(f"图片处理失败: {str(e)}")
            raise
    
    def _verify_video_file(self, video_path: Path) -> bool:
        """验证视频文件完整性"""
        try:
            # 检查文件大小
            if video_path.stat().st_size < 1024:  # 小于1KB可能是损坏的
                return False
            
            # 检查文件头部
            with open(video_path, 'rb') as f:
                header = f.read(8)
                # 检查常见视频格式的文件头
                if header.startswith(b'\x00\x00\x00\x20ftypmp4') or \
                   header.startswith(b'\x00\x00\x00\x18ftypmp4') or \
                   header[4:8] == b'ftyp':
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"视频文件验证失败: {str(e)}")
            return False
    
    def _get_image_metadata(self, image_path: Path) -> Dict[str, Any]:
        """获取图片元数据信息"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = image_path.stat().st_size
                file_ext = image_path.suffix.lower()
                content_type = Constants.FileConstants.CONTENT_TYPE_MAPPING.get(file_ext, 'image/jpeg')
                
                return {
                    'width': width,
                    'height': height,
                    'file_size': file_size,
                    'content_type': content_type,
                    'filename': image_path.name
                }
        except Exception as e:
            self.logger.error(f"获取图片元数据失败: {str(e)}")
            raise

    def _upload_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """步骤1：上传图片元数据，获取预签名URL"""
        try:
            # 构建请求数据
            payload = {
                "metadata": {
                    "image-height": str(metadata['height']),
                    "image-width": str(metadata['width'])
                },
                "scene": "vidu"
            }
            
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'zh',
                'Content-Type': 'application/json',
                'Origin': 'https://www.vidu.cn',
                'Referer': 'https://www.vidu.cn/',
                'X-App-Version': '-',
                'X-Platform': 'web'
            }
            
            self.logger.info("正在上传图片元数据...")
            
            # 发送元数据请求
            response = self.request_handler.post(
                Constants.APIEndpoints.FILES_UPLOADS_META,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                upload_id = result.get('id')
                put_url = result.get('put_url')
                
                if not upload_id or not put_url:
                    raise ValueError("响应中缺少必要的上传信息")
                
                self.logger.info(f"元数据上传成功，获得上传ID: {upload_id}")
                return {
                    'success': True,
                    'upload_id': upload_id,
                    'put_url': put_url,
                    'expires_at': result.get('expires_at')
                }
            else:
                error_msg = f"元数据上传失败，状态码: {response.status_code}"
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
            self.logger.error(f"元数据上传异常: {str(e)}")
            return {
                'success': False,
                'error': f'元数据上传异常: {str(e)}'
            }

    def _upload_binary_data(self, file_path: Path, put_url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """步骤2：上传图片二进制数据到预签名URL"""
        try:
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'zh,en;q=0.9,zh-CN;q=0.8',
                'Content-Type': metadata['content_type'],
                'Origin': 'https://www.vidu.cn',
                'Referer': 'https://www.vidu.cn/',
                'X-Amz-Meta-Image-Height': str(metadata['height']),
                'X-Amz-Meta-Image-Width': str(metadata['width'])
            }
            
            self.logger.info(f"正在上传图片二进制数据: {file_path.name}")
            
            # 从request_handler获取认证cookie
            auth_cookies = self.request_handler.get_session_cookies()
            
            # 读取并上传文件数据
            with open(file_path, 'rb') as file_data:
                # 使用requests.put但携带认证信息
                import requests
                response = requests.put(
                    put_url,
                    data=file_data.read(),
                    headers=headers,
                    cookies=auth_cookies,  # 传递认证cookie
                    timeout=60
                )
            
            if response.status_code in (200, 201, 204):
                self.logger.info("图片二进制数据上传成功")
                return {
                    'success': True,
                    'etag': response.headers.get('ETag', '').strip('"'),
                    'status_code': response.status_code
                }
            else:
                error_msg = f"二进制数据上传失败，状态码: {response.status_code}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            self.logger.error(f"二进制数据上传异常: {str(e)}")
            return {
                'success': False,
                'error': f'二进制数据上传异常: {str(e)}'
            }

    def _finish_upload(self, upload_id: str, etag: str) -> Dict[str, Any]:
        """步骤3：完成上传确认"""
        try:
            # 构建完成请求数据
            payload = {
                "etag": etag,
                "id": upload_id
            }
            
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'zh',
                'Content-Type': 'application/json',
                'Origin': 'https://www.vidu.cn',
                'Referer': 'https://www.vidu.cn/',
                'X-App-Version': '-',
                'X-Platform': 'web'
            }
            
            self.logger.info(f"正在完成上传确认，上传ID: {upload_id}")
            
            # 发送完成确认请求
            finish_url = Constants.APIEndpoints.FILES_UPLOADS_FINISH.format(upload_id=upload_id)
            response = self.request_handler.put(
                finish_url,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                file_uri = result.get('uri')
                
                if not file_uri:
                    raise ValueError("完成响应中缺少文件URI")
                
                self.logger.info(f"图片上传完成，文件URI: {file_uri}")
                return {
                    'success': True,
                    'file_uri': file_uri,
                    'upload_id': upload_id,
                    'finish_response': result
                }
            else:
                error_msg = f"完成上传失败，状态码: {response.status_code}"
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
            self.logger.error(f"完成上传异常: {str(e)}")
            return {
                'success': False,
                'error': f'完成上传异常: {str(e)}'
            }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值（ETag格式）"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储空间信息"""
        info = {}
        for name, path in self.storage_paths.items():
            if path.exists():
                files = list(path.glob('*'))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                info[name] = {
                    'path': str(path),
                    'file_count': len([f for f in files if f.is_file()]),
                    'total_size': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                }
        return info
    
    def cleanup_cache(self, max_age_hours: int = 24) -> int:
        """清理缓存文件"""
        cleaned_count = 0
        cache_path = self.storage_paths.get('cache')
        
        if not cache_path or not cache_path.exists():
            return cleaned_count
        
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        
        for file_path in cache_path.glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"清理缓存文件: {file_path.name}")
                    except Exception as e:
                        self.logger.error(f"清理文件失败 {file_path}: {str(e)}")
        
        if cleaned_count > 0:
            self.logger.info(f"缓存清理完成，清理了 {cleaned_count} 个文件")
        
        return cleaned_count
