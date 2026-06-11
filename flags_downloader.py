#!/usr/bin/env python3
"""
国旗图片批量下载程序 - 统一版本
支持异步和同步两种下载模式
"""

import os
import sys
import time
import glob
import json
import argparse
import urllib.request
import re
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
import ssl
import io
from PIL import Image
import asyncio
import aiohttp
import aiofiles

# 支持的所有尺寸选项
VALID_SIZES = [
    'w20', 'w40', 'w80', 'w160', 'w320', 'w640', 'w1280', 'w2560',
    'h20', 'h24', 'h40', 'h60', 'h80', 'h120', 'h240',
    '16x12', '20x15', '24x18', '28x21', '32x24', '36x27', '40x30',
    '48x36', '56x42', '60x45', '64x48', '72x54', '80x60', '84x63',
    '96x72', '108x81', '112x84', '120x90', '128x96', '144x108',
    '160x120', '192x144', '224x168', '256x192'
]

@dataclass
class DownloadTask:
    """下载任务数据结构"""
    country_code: str
    size: str
    format: str
    base_url: str = "https://flagcdn.com/"
    retry_count: int = 0
    last_error: str = None

# ============================================================================
# 公共函数（两种模式共享）
# ============================================================================

def download_and_generate_codes(json_path: str = "codes.json", txt_path: str = "codes.txt") -> bool:
    """
    从flagcdn.com下载国家代码JSON文件，并同时生成纯代码的TXT文件。
    
    返回:
    是否成功
    """
    try:
        print(f"正在从 https://flagcdn.com/zh/codes.json 下载国家代码...")
        
        url = "https://flagcdn.com/zh/codes.json"
        response = urllib.request.urlopen(url, timeout=30)
        data = json.loads(response.read().decode('utf-8'))
        
        # 1. 保存完整的JSON文件
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存完整数据到: {json_path}")
        
        # 2. 生成并保存纯代码的TXT文件
        country_codes = []
        for code in data.keys():
            if len(code) == 2 and code.isalpha():
                country_codes.append(code)
        country_codes.sort()
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            for code in country_codes:
                f.write(f"{code}\n")
        
        print(f"✓ 已提取 {len(country_codes)} 个有效国家代码到: {txt_path}")
        print(f"示例代码: {', '.join(country_codes[:5])}...")
        
        return True
        
    except Exception as e:
        print(f"下载或生成文件失败: {str(e)}")
        return False

def validate_size(size: str) -> bool:
    """验证尺寸参数是否有效"""
    if size not in VALID_SIZES:
        print(f"错误: 不支持的尺寸 '{size}'")
        print(f"支持的尺寸选项: {', '.join(VALID_SIZES[:10])}...")
        return False
    return True

def validate_format(format: str) -> bool:
    """验证格式参数是否有效"""
    valid_formats = ['png', 'webp', 'svg', 'jpg']
    return format.lower() in valid_formats

def safe_filename(name: str) -> str:
    """将字符串转换为安全的文件名（替换非法字符）"""
    name = name.replace(' ', '_')
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    if len(name) > 50:
        name = name[:50]
    return name

def read_country_codes(file_path: str) -> Tuple[List[str], Dict[str, str]]:
    """
    读取国家代码文件，支持两种格式：
    1. codes.txt: 每行一个两位国家代码
    2. codes.json: JSON格式，提取所有两位国家代码键
    
    返回:
    (country_codes, name_mapping)
    - country_codes: 有效的国家代码列表
    - name_mapping: 国家代码到国家名称的映射（仅对json文件有效）
    """
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return [], {}
    
    try:
        if file_path.lower().endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            country_codes = list(data.keys())
            valid_codes = []
            name_mapping = {}
            for code in country_codes:
                if len(code) == 2 and code.isalpha():
                    valid_codes.append(code)
                    if code in data:
                        name_mapping[code] = data[code]
            
            valid_codes.sort()
            print(f"从 {file_path} 读取了 {len(valid_codes)} 个有效的国家代码")
            return valid_codes, name_mapping
            
        elif file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                codes = [line.strip() for line in f if line.strip()]
            
            valid_codes = []
            for code in codes:
                if len(code) == 2 and code.isalpha():
                    valid_codes.append(code)
                else:
                    print(f"警告: 跳过无效的国家代码: {code}")
            
            valid_codes.sort()
            print(f"从 {file_path} 读取了 {len(valid_codes)} 个有效的国家代码")
            return valid_codes, {}
            
        else:
            print(f"错误: 不支持的文件格式 {file_path}，请使用 .txt 或 .json 文件")
            return [], {}
            
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        return [], {}
    except Exception as e:
        print(f"读取文件错误: {str(e)}")
        return [], {}

def get_default_sizes() -> List[str]:
    """获取默认尺寸列表"""
    return ["w80", "h60", "80x60"]

def get_output_dir(size: str, format: str, filename_format: str = "simple", 
                   include_country_name: bool = False) -> str:
    """获取输出目录"""
    base_dir = f"{size}_{format}"
    
    if filename_format == "full":
        base_dir += "_full"
    
    if include_country_name:
        base_dir += "_named"
    
    return base_dir

def get_filename(country_code: str, size: str, format: str, 
                 image_data: bytes = None, filename_format: str = "simple",
                 country_name: str = None, include_country_name: bool = False) -> str:
    """生成文件名"""
    if filename_format != "full":
        base_name = f"{country_code}_{size}"
    else:
        if 'x' in size and not size.startswith(('w', 'h')):
            try:
                width_str, height_str = size.split('x')
                width = int(width_str)
                height = int(height_str)
                base_name = f"{country_code}_{size}_{width}x{height}"
            except (ValueError, IndexError):
                base_name = f"{country_code}_{size}"
        else:
            if image_data and format.lower() != 'svg':
                try:
                    with Image.open(io.BytesIO(image_data)) as img:
                        width, height = img.size
                        base_name = f"{country_code}_{size}_{width}x{height}"
                except Exception:
                    base_name = f"{country_code}_{size}"
            else:
                base_name = f"{country_code}_{size}"
    
    if include_country_name and country_name:
        safe_name = safe_filename(country_name)
        return f"{base_name}_{safe_name}.{format}"
    
    return f"{base_name}.{format}"

def get_existing_files(output_dir: str) -> Dict[str, str]:
    """获取已存在的文件列表"""
    if not os.path.exists(output_dir):
        return {}
    
    existing_files = {}
    for file_path in glob.glob(os.path.join(output_dir, "*")):
        filename = os.path.basename(file_path)
        try:
            if '.' in filename:
                name_part = filename.split('.')[0]
                if '_' in name_part:
                    parts = name_part.split('_')
                    country_code = parts[0]
                    if country_code and len(country_code) == 2:
                        existing_files[country_code] = filename
        except:
            continue
    
    return existing_files

# ============================================================================
# 异步下载器实现
# ============================================================================

class AsyncFlagDownloader:
    """异步国旗下载器"""
    
    def __init__(self, max_concurrent: int = 20, timeout: int = 30, 
                 filename_format: str = "simple", include_country_name: bool = False,
                 name_mapping: Dict[str, str] = None):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.filename_format = filename_format
        self.include_country_name = include_country_name
        self.name_mapping = name_mapping or {}
        self.session = None
        self.ssl_context = None
        
    def _setup_ssl_context(self):
        """设置SSL上下文"""
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        return self.ssl_context
    
    async def download_single_flag(self, task: DownloadTask, output_dir: str, 
                                   force_redownload: bool = False) -> Tuple[bool, str]:
        """下载单个国旗图片"""
        
        existing_files = get_existing_files(output_dir)
        if not force_redownload and task.country_code in existing_files:
            filename = existing_files[task.country_code]
            file_path = os.path.join(output_dir, filename)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return True, f"文件已存在: {filename}"
        
        try:
            flag_url = f"{task.base_url}{task.size}/{task.country_code}.{task.format}"
            
            async with self.session.get(flag_url, ssl=self.ssl_context, 
                                        timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                
                if response.status == 200:
                    image_data = await response.read()
                    
                    country_name = self.name_mapping.get(task.country_code) if self.include_country_name else None
                    
                    filename = get_filename(
                        task.country_code, 
                        task.size, 
                        task.format, 
                        image_data, 
                        self.filename_format,
                        country_name,
                        self.include_country_name
                    )
                    file_path = os.path.join(output_dir, filename)
                    
                    os.makedirs(output_dir, exist_ok=True)
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(image_data)
                    
                    return True, f"下载成功: {filename}"
                else:
                    return False, f"HTTP错误: {response.status}"
                    
        except Exception as e:
            return False, f"下载失败: {str(e)}"
    
    async def download_batch(self, tasks: List[DownloadTask], output_dir: str, 
                            force_redownload: bool = False, max_retries: int = 2) -> Dict:
        """批量下载国旗图片"""
        self._setup_ssl_context()
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context, limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            
            existing_files = get_existing_files(output_dir)
            existing_country_codes = set(existing_files.keys())
            
            download_tasks = []
            skipped_codes = []
            
            for task in tasks:
                if not force_redownload and task.country_code in existing_country_codes:
                    skipped_codes.append(task.country_code)
                else:
                    download_tasks.append(task)
            
            print(f"总任务数: {len(tasks)}")
            print(f"跳过已存在: {len(skipped_codes)}")
            print(f"需要下载: {len(download_tasks)}")
            
            if not download_tasks:
                return {
                    'success': [],
                    'failed': [],
                    'skipped': skipped_codes,
                    'total_time': 0
                }
            
            all_success = []
            all_failed = []
            remaining_tasks = download_tasks.copy()
            
            for retry_round in range(max_retries + 1):
                if not remaining_tasks:
                    break
                
                if retry_round == 0:
                    print(f"\n第 1 轮下载（首次尝试）:")
                else:
                    print(f"\n第 {retry_round + 1} 轮下载（重试 {retry_round} 次后）:")
                    await asyncio.sleep(2)
                
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def download_with_semaphore(task):
                    async with semaphore:
                        return await self.download_single_flag(task, output_dir, force_redownload)
                
                current_tasks = [download_with_semaphore(task) for task in remaining_tasks]
                
                print(f"并发下载 {len(current_tasks)} 个文件，最大并发数: {self.max_concurrent}")
                
                current_success = []
                current_failed = []
                
                batch_size = 10
                for i in range(0, len(current_tasks), batch_size):
                    batch = current_tasks[i:i+batch_size]
                    results = await asyncio.gather(*batch, return_exceptions=True)
                    
                    for j, result in enumerate(results):
                        task_index = i + j
                        if task_index < len(remaining_tasks):
                            country_code = remaining_tasks[task_index].country_code
                            
                            if isinstance(result, Exception):
                                current_failed.append((country_code, f"任务异常: {str(result)}"))
                                print(f"  {country_code.upper()}: ✗ 异常: {str(result)}")
                            else:
                                success, message = result
                                if success:
                                    current_success.append(country_code)
                                    print(f"  {country_code.upper()}: ✓ {message}")
                                else:
                                    current_failed.append((country_code, message))
                                    print(f"  {country_code.upper()}: ✗ {message}")
                    
                    processed = min(i + batch_size, len(current_tasks))
                    print(f"  进度: {processed}/{len(current_tasks)}")
                    await asyncio.sleep(0.1)
                
                all_success.extend(current_success)
                
                remaining_tasks = []
                for country_code, error_msg in current_failed:
                    original_task = next((t for t in download_tasks if t.country_code == country_code), None)
                    if original_task:
                        new_task = DownloadTask(
                            country_code=original_task.country_code,
                            size=original_task.size,
                            format=original_task.format,
                            base_url=original_task.base_url,
                            retry_count=original_task.retry_count + 1,
                            last_error=error_msg
                        )
                        remaining_tasks.append(new_task)
                
                print(f"本轮结果: 成功 {len(current_success)}, 失败 {len(current_failed)}")
                
                if not remaining_tasks or retry_round >= max_retries:
                    for country_code, error_msg in current_failed:
                        all_failed.append((country_code, error_msg))
                    break
            
            return {
                'success': all_success,
                'failed': all_failed,
                'skipped': skipped_codes,
                'total_time': 0
            }

# ============================================================================
# 同步下载器实现（备用）
# ============================================================================

class SyncFlagDownloader:
    """同步国旗下载器（使用requests和多线程）"""
    
    def __init__(self, max_workers: int = 20, timeout: int = 30,
                 filename_format: str = "simple", include_country_name: bool = False,
                 name_mapping: Dict[str, str] = None):
        self.max_workers = max_workers
        self.timeout = timeout
        self.filename_format = filename_format
        self.include_country_name = include_country_name
        self.name_mapping = name_mapping or {}
        self.session = None
        
    def _setup_session(self):
        """设置requests会话"""
        import requests
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def download_single_flag(self, task: DownloadTask, output_dir: str, 
                             force_redownload: bool = False) -> Tuple[bool, str]:
        """下载单个国旗图片"""
        
        existing_files = get_existing_files(output_dir)
        if not force_redownload and task.country_code in existing_files:
            filename = existing_files[task.country_code]
            file_path = os.path.join(output_dir, filename)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return True, f"文件已存在: {filename}"
        
        try:
            import requests
            
            flag_url = f"{task.base_url}{task.size}/{task.country_code}.{task.format}"
            response = self.session.get(flag_url, timeout=self.timeout)
            
            if response.status_code == 200:
                image_data = response.content
                
                country_name = self.name_mapping.get(task.country_code) if self.include_country_name else None
                
                filename = get_filename(
                    task.country_code, 
                    task.size, 
                    task.format,
                    image_data, 
                    self.filename_format,
                    country_name,
                    self.include_country_name
                )
                file_path = os.path.join(output_dir, filename)
                
                os.makedirs(output_dir, exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
                return True, f"下载成功: {filename}"
            else:
                return False, f"HTTP错误: {response.status_code}"
                    
        except Exception as e:
            return False, f"下载失败: {str(e)}"
    
    def download_batch(self, tasks: List[DownloadTask], output_dir: str, 
                       force_redownload: bool = False, max_retries: int = 2) -> Dict:
        """批量下载国旗图片（使用线程池）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self._setup_session()
        
        existing_files = get_existing_files(output_dir)
        existing_country_codes = set(existing_files.keys())
        
        download_tasks = []
        skipped_codes = []
        
        for task in tasks:
            if not force_redownload and task.country_code in existing_country_codes:
                skipped_codes.append(task.country_code)
            else:
                download_tasks.append(task)
        
        print(f"总任务数: {len(tasks)}")
        print(f"跳过已存在: {len(skipped_codes)}")
        print(f"需要下载: {len(download_tasks)}")
        
        if not download_tasks:
            return {
                'success': [],
                'failed': [],
                'skipped': skipped_codes,
                'total_time': 0
            }
        
        all_success = []
        all_failed = []
        remaining_tasks = download_tasks.copy()
        
        for retry_round in range(max_retries + 1):
            if not remaining_tasks:
                break
            
            if retry_round == 0:
                print(f"\n第 1 轮下载（首次尝试）:")
            else:
                print(f"\n第 {retry_round + 1} 轮下载（重试 {retry_round} 次后）:")
                time.sleep(2)
            
            current_success = []
            current_failed = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self.download_single_flag, task, output_dir, force_redownload): task
                    for task in remaining_tasks
                }
                
                completed_count = 0
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    completed_count += 1
                    
                    try:
                        success, message = future.result()
                        if success:
                            current_success.append(task.country_code)
                            print(f"  {task.country_code.upper()}: ✓ {message}")
                        else:
                            current_failed.append((task.country_code, message))
                            print(f"  {task.country_code.upper()}: ✗ {message}")
                    except Exception as e:
                        current_failed.append((task.country_code, f"任务异常: {str(e)}"))
                        print(f"  {task.country_code.upper()}: ✗ 异常: {str(e)}")
                    
                    if completed_count % 10 == 0 or completed_count == len(remaining_tasks):
                        print(f"  进度: {completed_count}/{len(remaining_tasks)}")
            
            all_success.extend(current_success)
            
            remaining_tasks = []
            for country_code, error_msg in current_failed:
                original_task = next((t for t in download_tasks if t.country_code == country_code), None)
                if original_task:
                    new_task = DownloadTask(
                        country_code=original_task.country_code,
                        size=original_task.size,
                        format=original_task.format,
                        base_url=original_task.base_url,
                        retry_count=original_task.retry_count + 1,
                        last_error=error_msg
                    )
                    remaining_tasks.append(new_task)
            
            print(f"本轮结果: 成功 {len(current_success)}, 失败 {len(current_failed)}")
            
            if not remaining_tasks or retry_round >= max_retries:
                for country_code, error_msg in current_failed:
                    all_failed.append((country_code, error_msg))
                break
        
        return {
            'success': all_success,
            'failed': all_failed,
            'skipped': skipped_codes,
            'total_time': 0
        }

# ============================================================================
# 主程序逻辑
# ============================================================================

def check_dependencies(mode: str) -> Tuple[bool, str]:
    """检查依赖是否已安装"""
    if mode == 'async':
        try:
            import aiohttp
            import aiofiles
            import asyncio
            return True, None
        except ImportError as e:
            return False, "异步模式需要安装: pip install aiohttp aiofiles"
    
    elif mode == 'sync':
        try:
            import requests
            return True, None
        except ImportError as e:
            return False, "同步模式需要安装: pip install requests"
    
    return True, None

def print_banner():
    """打印程序横幅"""
    banner = """
==================================================
      国旗图片批量下载程序
      National Flag Image Downloader
==================================================
    """
    print(banner)

def print_mode_info():
    """打印下载模式信息"""
    print("下载模式说明:")
    print("  异步模式 (async): 使用aiohttp异步下载，性能更高")
    print("  同步模式 (sync): 使用requests多线程下载，兼容性更好")

def print_filename_format_info():
    """打印文件名格式信息"""
    print("文件名格式说明:")
    print("  simple: {国家代码}_{尺寸}.{格式} (默认)")
    print("  full: {国家代码}_{尺寸}_{宽度}x{高度}.{格式}")

async def async_main(args, country_codes, name_mapping):
    """异步主程序"""
    sizes = []
    if args.sizes:
        sizes = [s.strip() for s in args.sizes.split(',') if s.strip()]
    elif args.sizes_file:
        try:
            with open(args.sizes_file, 'r', encoding='utf-8') as f:
                sizes = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"错误: 找不到尺寸文件 {args.sizes_file}")
            return None, 0
    
    if not sizes:
        sizes = get_default_sizes()
        print(f"使用默认尺寸列表，共 {len(sizes)} 个尺寸")
        print(f"默认尺寸: {', '.join(sizes)}")
    
    invalid_sizes = [s for s in sizes if s not in VALID_SIZES]
    if invalid_sizes:
        print(f"错误: 不支持的尺寸: {invalid_sizes}")
        return None, 0
    
    formats = [f.strip().lower() for f in args.formats.split(',') if f.strip()]
    invalid_formats = [f for f in formats if not validate_format(f)]
    if invalid_formats:
        print(f"错误: 不支持的图片格式: {invalid_formats}")
        print("支持的格式: png, webp, svg, jpg")
        return None, 0
    
    print("=" * 60)
    print(f"国家数量: {len(country_codes)}")
    print(f"尺寸数量: {len(sizes)}")
    print(f"格式数量: {len(formats)}")
    print(f"总任务数: {len(country_codes) * len(sizes) * len(formats)}")
    print(f"最大并发数: {args.concurrent}")
    print(f"最大重试次数: {args.max_retries}")
    print(f"请求超时: {args.timeout}秒")
    print(f"文件名格式: {args.filename_format}")
    print(f"包含国家名称: {'是' if args.include_country_name else '否'}")
    
    if args.force:
        print("强制重新下载: 是")
    
    if args.filename_format == "full":
        print("注意: 使用完整文件名格式会增加少量处理时间")
    
    if args.include_country_name:
        if args.file.lower().endswith('.json'):
            print("注意: 使用包含国家名称的文件名格式")
        else:
            print("注意: 输入文件不是json格式，无法包含国家名称")
    
    tasks = []
    for country_code in country_codes:
        for size in sizes:
            for format in formats:
                tasks.append(DownloadTask(
                    country_code=country_code,
                    size=size,
                    format=format
                ))
    
    estimated_time = len(tasks) * 0.5 / args.concurrent
    if args.filename_format == "full":
        estimated_time *= 1.1
    if args.include_country_name:
        estimated_time *= 1.05
    print(f"预计下载时间: {estimated_time/60:.1f} 分钟")
    
    all_results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'total_time': 0
    }
    
    for format in formats:
        print(f"\n开始下载 {format.upper()} 格式图片...")
        print("-" * 40)
        
        format_tasks = [t for t in tasks if t.format == format]
        
        for size in sizes:
            print(f"\n尺寸: {size}")
            
            size_tasks = [t for t in format_tasks if t.size == size]
            
            downloader = AsyncFlagDownloader(
                max_concurrent=args.concurrent,
                timeout=args.timeout,
                filename_format=args.filename_format,
                include_country_name=args.include_country_name,
                name_mapping=name_mapping
            )
            
            try:
                output_dir = get_output_dir(size, format, args.filename_format, args.include_country_name)
                result = await downloader.download_batch(
                    tasks=size_tasks,
                    output_dir=output_dir,
                    force_redownload=args.force,
                    max_retries=args.max_retries
                )
                
                all_results['success'].extend(result['success'])
                all_results['failed'].extend(result['failed'])
                all_results['skipped'].extend(result['skipped'])
                all_results['total_time'] += result['total_time']
                
                print(f"  成功: {len(result['success'])}, 失败: {len(result['failed'])}, 跳过: {len(result['skipped'])}")
                
            except Exception as e:
                print(f"  下载出错: {str(e)}")
    
    return all_results, len(tasks)

def sync_main(args, country_codes, name_mapping):
    """同步主程序"""
    sizes = []
    if args.sizes:
        sizes = [s.strip() for s in args.sizes.split(',') if s.strip()]
    elif args.sizes_file:
        try:
            with open(args.sizes_file, 'r', encoding='utf-8') as f:
                sizes = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"错误: 找不到尺寸文件 {args.sizes_file}")
            return None, 0
    
    if not sizes:
        sizes = get_default_sizes()
        print(f"使用默认尺寸列表，共 {len(sizes)} 个尺寸")
        print(f"默认尺寸: {', '.join(sizes)}")
    
    invalid_sizes = [s for s in sizes if s not in VALID_SIZES]
    if invalid_sizes:
        print(f"错误: 不支持的尺寸: {invalid_sizes}")
        return None, 0
    
    formats = [f.strip().lower() for f in args.formats.split(',') if f.strip()]
    invalid_formats = [f for f in formats if not validate_format(f)]
    if invalid_formats:
        print(f"错误: 不支持的图片格式: {invalid_formats}")
        print("支持的格式: png, webp, svg, jpg")
        return None, 0
    
    print("=" * 60)
    print(f"国家数量: {len(country_codes)}")
    print(f"尺寸数量: {len(sizes)}")
    print(f"格式数量: {len(formats)}")
    print(f"总任务数: {len(country_codes) * len(sizes) * len(formats)}")
    print(f"最大线程数: {args.concurrent}")
    print(f"最大重试次数: {args.max_retries}")
    print(f"请求超时: {args.timeout}秒")
    print(f"文件名格式: {args.filename_format}")
    print(f"包含国家名称: {'是' if args.include_country_name else '否'}")
    
    if args.force:
        print("强制重新下载: 是")
    
    if args.filename_format == "full":
        print("注意: 使用完整文件名格式会增加少量处理时间")
    
    if args.include_country_name:
        if args.file.lower().endswith('.json'):
            print("注意: 使用包含国家名称的文件名格式")
        else:
            print("注意: 输入文件不是json格式，无法包含国家名称")
    
    tasks = []
    for country_code in country_codes:
        for size in sizes:
            for format in formats:
                tasks.append(DownloadTask(
                    country_code=country_code,
                    size=size,
                    format=format
                ))
    
    estimated_time = len(tasks) * 0.5 / args.concurrent
    if args.filename_format == "full":
        estimated_time *= 1.1
    if args.include_country_name:
        estimated_time *= 1.05
    print(f"预计下载时间: {estimated_time/60:.1f} 分钟")
    
    all_results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'total_time': 0
    }
    
    for format in formats:
        print(f"\n开始下载 {format.upper()} 格式图片...")
        print("-" * 40)
        
        format_tasks = [t for t in tasks if t.format == format]
        
        for size in sizes:
            print(f"\n尺寸: {size}")
            
            size_tasks = [t for t in format_tasks if t.size == size]
            
            downloader = SyncFlagDownloader(
                max_workers=args.concurrent,
                timeout=args.timeout,
                filename_format=args.filename_format,
                include_country_name=args.include_country_name,
                name_mapping=name_mapping
            )
            
            try:
                output_dir = get_output_dir(size, format, args.filename_format, args.include_country_name)
                result = downloader.download_batch(
                    tasks=size_tasks,
                    output_dir=output_dir,
                    force_redownload=args.force,
                    max_retries=args.max_retries
                )
                
                all_results['success'].extend(result['success'])
                all_results['failed'].extend(result['failed'])
                all_results['skipped'].extend(result['skipped'])
                all_results['total_time'] += result['total_time']
                
                print(f"  成功: {len(result['success'])}, 失败: {len(result['failed'])}, 跳过: {len(result['skipped'])}")
                
            except Exception as e:
                print(f"  下载出错: {str(e)}")
    
    return all_results, len(tasks)

def print_results(all_results, total_tasks, mode, start_time, filename_format, include_country_name):
    """打印下载结果"""
    end_time = time.time()
    
    print("\n" + "=" * 60)
    print("所有下载任务完成!")
    print(f"下载模式: {mode}")
    print(f"文件名格式: {filename_format}")
    print(f"包含国家名称: {'是' if include_country_name else '否'}")
    print(f"总任务数: {total_tasks}")
    print(f"成功下载: {len(all_results['success'])}")
    print(f"跳过已存在: {len(all_results['skipped'])}")
    print(f"最终失败: {len(all_results['failed'])}")
    print(f"下载耗时: {all_results['total_time']:.2f} 秒")
    print(f"总执行时间: {end_time - start_time:.2f} 秒")
    
    if all_results['success']:
        print(f"\n成功下载的文件数量: {len(all_results['success'])}")
    
    if all_results['failed']:
        print(f"\n失败的任务数量: {len(all_results['failed'])}")
        
        error_counts = {}
        for country_code, error_msg in all_results['failed']:
            error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        print("失败原因统计:")
        for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error_type}: {count} 次")
        
        failed_file = f"failed_downloads_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(failed_file, 'w', encoding='utf-8') as f:
            f.write(f"下载失败的任务列表（重试后仍失败）\n")
            f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"文件名格式: {filename_format}\n")
            f.write(f"包含国家名称: {'是' if include_country_name else '否'}\n")
            f.write("=" * 50 + "\n")
            for country_code, error_msg in all_results['failed']:
                f.write(f"{country_code}: {error_msg}\n")
        
        print(f"\n失败列表已保存到: {failed_file}")
    
    print(f"\n文件命名格式示例:")
    if filename_format == "simple":
        if include_country_name:
            print("  {国家代码}_{尺寸}_{国家名称}.{格式}")
            print("  例如: cn_w80_中国.png, us_256x192_美国.webp")
        else:
            print("  {国家代码}_{尺寸}.{格式}")
            print("  例如: cn_w80.png, us_256x192.webp")
    else:
        if include_country_name:
            print("  {国家代码}_{尺寸}_{宽度}x{高度}_{国家名称}.{格式}")
            print("  例如: cn_w80_40x80_中国.png, us_256x192_512x384_美国.webp")
        else:
            print("  {国家代码}_{尺寸}_{宽度}x{高度}.{格式}")
            print("  例如: cn_w80_40x80.png, us_256x192_512x384.webp")

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='国旗图片批量下载程序 - 统一版本')
    parser.add_argument('file', nargs='?', default='codes.txt',
                       help='国家代码文件路径 (默认: codes.txt，也支持 codes.json)')
    parser.add_argument('--sizes', default=None,
                       help='尺寸列表，用逗号分隔，如 "w80,16x12,256x192"')
    parser.add_argument('--sizes-file', default=None,
                       help='尺寸列表文件路径，每行一个尺寸')
    parser.add_argument('--formats', default='png',
                       help='图片格式列表，用逗号分隔 (默认: png, 选项: png,webp,svg,jpg)')
    parser.add_argument('--force', '-f', action='store_true',
                       help='强制重新下载所有文件')
    parser.add_argument('--concurrent', '-c', type=int, default=20,
                       help='最大并发数/线程数 (默认: 20)')
    parser.add_argument('--max-retries', '-r', type=int, default=2,
                       help='最大重试次数 (默认: 2)')
    parser.add_argument('--timeout', '-t', type=int, default=30,
                       help='请求超时时间(秒) (默认: 30)')
    parser.add_argument('--list-sizes', '-l', action='store_true',
                       help='列出所有支持的尺寸选项')
    parser.add_argument('--mode', '-m', choices=['async', 'sync'], default='async',
                       help='下载模式: async(异步, 默认) 或 sync(同步)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='跳过确认提示，直接开始下载')
    parser.add_argument('--filename-format', '--ff', choices=['simple', 'full'], 
                       default='simple', 
                       help='文件名格式: simple(默认，{国家代码}_{尺寸}.{格式}) 或 full(完整，{国家代码}_{尺寸}_{宽}x{高}.{格式})')
    parser.add_argument('--include-country-name', '--icn', action='store_true',
                       help='在文件名中包含国家名称（仅对json文件有效）')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.list_sizes:
        print("所有支持的尺寸选项:")
        print("宽度固定 (w开头):")
        w_sizes = [s for s in VALID_SIZES if s.startswith('w')]
        for size in w_sizes:
            print(f"  {size}")
        
        print("\n高度固定 (h开头):")
        h_sizes = [s for s in VALID_SIZES if s.startswith('h')]
        for size in h_sizes:
            print(f"  {size}")
        
        print("\n精确尺寸 (宽度x高度):")
        exact_sizes = [s for s in VALID_SIZES if 'x' in s and not s.startswith(('w', 'h'))]
        for size in exact_sizes:
            print(f"  {size}")
        
        print(f"\n总计: {len(VALID_SIZES)} 个尺寸选项")
        print(f"\n默认尺寸: {', '.join(get_default_sizes())}")
        print("\n文件名格式说明:")
        print_filename_format_info()
        print("包含国家名称说明:")
        print("  --include-country-name: 在文件名中包含国家名称（仅对json文件有效）")
        return 0
    
    success, error_msg = check_dependencies(args.mode)
    if not success:
        print(f"错误: {error_msg}")
        print("请安装所需依赖后重试")
        return 1
    
    if not os.path.exists(args.file):
        print(f"注意: 找不到文件 {args.file}")
        
        possible_files = []
        
        if os.path.exists("codes.json"):
            possible_files.append("codes.json")
        
        if os.path.exists("codes.txt"):
            possible_files.append("codes.txt")
        
        if os.path.exists("countries.txt"):
            possible_files.append("countries.txt")
        
        if possible_files:
            print(f"找到以下可能的国家代码文件: {', '.join(possible_files)}")
            print(f"请指定正确的文件名，例如: python flags-downloader.py {possible_files[0]}")
            return 1
        else:
            print("正在尝试下载并生成国家代码文件...")
            if download_and_generate_codes("codes.json", "codes.txt"):
                print(f"✓ 已成功创建 codes.json 和 codes.txt 文件")
                if args.file == "codes.txt":
                    pass
                elif args.file == "codes.json":
                    pass
                elif args.file not in ["codes.txt", "codes.json"]:
                    args.file = "codes.txt"
                    print(f"将使用 {args.file} 继续执行")
            else:
                print(f"错误: 无法从远程下载国家代码文件，下载已取消")
                print(f"请手动创建 {args.file} 文件，或检查网络连接后重试")
                print("文件格式: 每行一个国家的二位代码（小写），或使用 codes.json 格式")
                return 1
    
    # 只读取一次国家代码
    country_codes, name_mapping = read_country_codes(args.file)
    if not country_codes:
        print("错误: 文件内容为空或没有有效的国家代码")
        return 1
    
    if args.include_country_name and not args.file.lower().endswith('.json'):
        print(f"警告: 输入文件 {args.file} 不是json格式，无法包含国家名称")
        print("将使用标准文件名格式")
        args.include_country_name = False
    
    print_mode_info()
    print(f"\n当前配置:")
    print(f"  下载模式: {args.mode}")
    print(f"  国家代码文件: {args.file}")
    print(f"  图片格式: {args.formats}")
    print(f"  文件名格式: {args.filename_format}")
    print(f"  包含国家名称: {'是' if args.include_country_name else '否'}")
    print(f"  最大并发数: {args.concurrent}")
    print(f"  最大重试次数: {args.max_retries}")
    print(f"  超时时间: {args.timeout}秒")
    
    if args.force:
        print("  强制重新下载: 是")
    
    if args.sizes:
        print(f"  指定尺寸: {args.sizes}")
    elif args.sizes_file:
        print(f"  尺寸文件: {args.sizes_file}")
    else:
        print("  使用默认尺寸: w80, h60, 80x60")
    
    if args.yes:
        print("  跳过确认: 是")
    
    print_filename_format_info()
    
    if not args.yes:
        confirm = input("\n是否开始下载? (y/n): ").lower()
        if confirm != 'y':
            print("下载已取消")
            return 0
    
    start_time = time.time()
    
    try:
        if args.mode == 'async':
            all_results, total_tasks = asyncio.run(async_main(args, country_codes, name_mapping))
        else:
            all_results, total_tasks = sync_main(args, country_codes, name_mapping)
        
        if all_results is not None:
            print_results(all_results, total_tasks, args.mode, start_time, args.filename_format, args.include_country_name)
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n\n下载被用户中断")
        return 1
    except Exception as e:
        print(f"\n程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())