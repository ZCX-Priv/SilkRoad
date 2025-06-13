import ssl
import re
import random
import string
import time
import json
import socket
import http.server
import http.client
import datetime
from http import HTTPStatus
from socketserver import ThreadingMixIn
from urllib import parse
from threading import Timer, Thread
from publicsuffix2 import PublicSuffixList
import httpx
import gc
import atexit
import shutil
import os
import signal
import sys
import platform
from loguru import logger
import glob
import queue
import concurrent.futures
import threading

def preload_streamed_response_content_async(response_obj, buffer_queue, chunk_size=8192):
    """异步预加载响应内容到缓冲队列"""
    try:
        for chunk in response_obj.iter_bytes(chunk_size):
            try:
                buffer_queue.put(chunk, timeout=10)
            except queue.Full:
                logger.error("缓冲队列已满，无法继续预加载")
                break
        # 放入结束标记
        buffer_queue.put(None, timeout=10)
    except Exception as e:
        logger.error(f"预加载响应内容时出错: {e}")
        buffer_queue.put(None, timeout=10)
    finally:
        # 确保线程正常退出
        return

# ------------------ 配置与数据加载 ------------------
with open('databases/config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

with open('databases/users.json', 'r', encoding='utf-8') as users_file:
    users_data = json.load(users_file)

# 设置默认的持久连接参数
config.setdefault("ENABLE_KEEP_ALIVE", True)  # 默认启用持久连接
config.setdefault("KEEP_ALIVE_TIMEOUT", 60)  # 持久连接超时时间（秒）
config.setdefault("KEEP_ALIVE_MAX", 100)  # 单个连接最大请求数

# 设置 http.client 最大请求头数量，修复 "get more than 100 headers" 错误
http.client._MAXHEADERS = 1000

# ------------------ 系统与资源管理 ------------------
def periodic_gc():
    """定时释放内存，每1分钟执行一次垃圾回收"""
    gc.collect()
    Timer(60, periodic_gc).start()

periodic_gc()

def clear_temp_cache():
    """程序退出时清除 temp 文件夹中的缓存（包括编译后的 .pyc 与网站缓存）"""
    # 确保使用程序所在目录
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    if os.path.exists(temp_dir):
        try:
            # 先关闭所有打开的文件句柄
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # 尝试打开并立即关闭文件,释放文件句柄
                        with open(file_path, 'rb'):
                            pass
                    except:
                        pass
            
            # 等待100ms让系统完全释放文件句柄
            time.sleep(0.1)
            
            # 删除目录树
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 确认目录是否被删除,如果没有则强制删除
            if os.path.exists(temp_dir):
                os.system(f'rd /s /q "{temp_dir}"' if platform.system() == 'Windows' else f'rm -rf "{temp_dir}"')
            
            logger.info("已清除临时缓存目录。")
        except Exception as e:
            logger.error(f"清除缓存目录时出错: {e}")

# 注册清理函数
atexit.register(clear_temp_cache)

# ------------------ 脚本管理 ------------------
class ScriptManager:
    """管理自定义JS脚本的类"""
    def __init__(self):
        self.scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
        self.scripts_cache = {}
        self.last_load_time = 0
        self.cache_ttl = 60  # 缓存有效期（秒）
        
        # 确保脚本目录存在
        if not os.path.exists(self.scripts_dir):
            os.makedirs(self.scripts_dir)
            logger.info(f"创建脚本目录: {self.scripts_dir}")
    
    def get_all_scripts(self):
        """获取所有JS脚本内容"""
        current_time = time.time()
        
        # 如果缓存未过期，直接返回缓存内容
        if current_time - self.last_load_time < self.cache_ttl and self.scripts_cache:
            return self.scripts_cache
        
        # 重新加载所有脚本
        scripts = {}
        script_files = glob.glob(os.path.join(self.scripts_dir, "*.js"))
        
        for script_path in script_files:
            try:
                script_name = os.path.basename(script_path)
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                scripts[script_name] = script_content
                logger.debug(f"加载脚本: {script_name}")
            except Exception as e:
                logger.error(f"加载脚本 {script_path} 失败: {e}")
        
        # 更新缓存
        self.scripts_cache = scripts
        self.last_load_time = current_time
        
        return scripts

# 初始化脚本管理器
script_manager = ScriptManager()

# ------------------ HTTP连接池管理 ------------------
class HttpClientPool:
    def __init__(self, pool_size=100):
        self.clients = []
        self.max_clients = pool_size
        self.lock = threading.Lock()
        self.session_map = {}
        self.domain_session_map = {}
    
    def init_pool(self):
        # 此方法不再使用，保留为空以兼容现有代码
        pass
    
    def get_client(self, domain=None):
        """获取一个可用的客户端，优先返回与指定域名关联的客户端"""
        with self.lock:
            # 如果指定了域名，尝试获取该域名的专用客户端
            if domain and domain in self.domain_session_map:
                return self.domain_session_map[domain]
            
            # 否则从通用池中获取
            if not self.clients:
                # 创建一个新的客户端
                # 创建自定义SSL上下文
                ssl_context = ssl.create_default_context()
                # 配置支持的协议版本
                ssl_context.options |= ssl.OP_NO_SSLv2
                ssl_context.options |= ssl.OP_NO_SSLv3
                # 设置密码套件优先级
                ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
                
                client = httpx.Client(
                    http2=config.get("HTTP", {}).get("ENABLE_HTTP2", True),
                    verify=False,
                    timeout=config.get("HTTP", {}).get("TIMEOUT", 30.0),
                    follow_redirects=False,
                    transport=httpx.HTTPTransport(
                        retries=config.get("HTTP", {}).get("MAX_RETRIES", 2),
                        # 使用自定义SSL上下文
                        verify=ssl_context
                    )
                )
                
                # 如果指定了域名，将此客户端与域名关联
                if domain:
                    self.domain_session_map[domain] = client
                    
                return client
            return self.clients.pop()
    
    def release_client(self, client, domain=None):
        """释放客户端回连接池"""
        with self.lock:
            # 如果客户端与特定域名关联，保持关联
            if domain and domain in self.domain_session_map and self.domain_session_map[domain] == client:
                return
                
            # 否则放回通用池
            if len(self.clients) < self.max_clients:
                self.clients.append(client)
            else:
                # 如果池已满，关闭客户端
                client.close()
    
    def clear(self):
        """清空连接池"""
        with self.lock:
            for client in self.clients:
                client.close()
            self.clients.clear()
            
            # 清空域名关联的客户端
            for domain, client in self.domain_session_map.items():
                client.close()
            self.domain_session_map.clear()

# ------------------ 缓存管理类 ------------------
class CacheManager:
    """管理系统缓存的类"""
    def __init__(self):
        # 使用程序所在目录
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        self.html_cache_dir = os.path.join(self.base_dir, "html")
        self.media_cache_dir = os.path.join(self.base_dir, "media")
        self.response_cache_dir = os.path.join(self.base_dir, "responses")
        
        # 从配置文件中读取缓存设置
        cache_control = config.get("CACHE_CONTROL", {})
        self.max_cache_size = cache_control.get("MAX_SIZE", 500 * 1024 * 1024)  # 默认500MB
        self.max_cache_age = cache_control.get("MAX_AGE", 24 * 60 * 60)  # 默认24小时
        
        self.cache_enabled = config.get("CACHE_ENABLED", True)  # 默认启用缓存
        self.cache_html = config.get("CACHE_HTML", True)  # 默认缓存HTML
        self.cache_media = config.get("CACHE_MEDIA", True)  # 默认缓存媒体文件
        self.cache_other = config.get("CACHE_OTHER", True)  # 默认缓存其他响应
        self.cache_large_files = config.get("CACHE_LARGE_FILES", False)  # 默认不缓存大文件
        
        # 缓存控制策略
        self.cache_control_by_mime = cache_control.get("BY_MIME", {})
        
        # 确保缓存目录存在
        self._ensure_cache_dirs()
        
        # 启动定期清理任务
        self._schedule_cleanup()
        
        logger.info(f"缓存状态: {'启用' if self.cache_enabled else '禁用'}")
        if self.cache_enabled:
            logger.info(f"缓存配置: HTML({'启用' if self.cache_html else '禁用'}), "
                       f"媒体文件({'启用' if self.cache_media else '禁用'}), "
                       f"其他响应({'启用' if self.cache_other else '禁用'}), "
                       f"大文件({'启用' if self.cache_large_files else '禁用'})")
    def _ensure_cache_dirs(self):
        """确保所有缓存目录存在"""
        for dir_path in [self.base_dir, self.html_cache_dir, 
                         self.media_cache_dir, self.response_cache_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.debug(f"创建缓存目录: {dir_path}")
    
    def _schedule_cleanup(self):
        """安排定期清理任务"""
        cleanup_interval = 3600  # 每小时清理一次
        Timer(cleanup_interval, self._cleanup_cache).start()
    
    def _cleanup_cache(self):
        """清理过期和过大的缓存"""
        try:
            logger.info("开始清理缓存...")
            now = time.time()
            total_size = 0
            files_info = []
            
            # 收集所有缓存文件信息
            for root, _, files in os.walk(self.base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_stat = os.stat(file_path)
                        file_size = file_stat.st_size
                        file_mtime = file_stat.st_mtime
                        total_size += file_size
                        files_info.append((file_path, file_size, file_mtime))
                    except (FileNotFoundError, PermissionError) as e:
                        logger.warning(f"无法获取文件信息 {file_path}: {e}")
            
            # 删除过期文件
            expired_files = [(path, size) for path, size, mtime in files_info 
                            if now - mtime > self.max_cache_age]
            for path, size in expired_files:
                try:
                    os.remove(path)
                    total_size -= size
                    logger.debug(f"删除过期缓存文件: {path}")
                except (FileNotFoundError, PermissionError) as e:
                    logger.warning(f"无法删除文件 {path}: {e}")
            
            # 如果缓存仍然过大，按最后访问时间排序删除
            if total_size > self.max_cache_size:
                remaining_files = [(path, size, mtime) for path, size, mtime in files_info 
                                if not any(path == exp_path for exp_path, _ in expired_files)]
                remaining_files.sort(key=lambda x: x[2])  # 按修改时间排序
                
                for path, size, _ in remaining_files:
                    if total_size <= self.max_cache_size:
                        break
                    try:
                        os.remove(path)
                        total_size -= size
                        logger.debug(f"删除过大缓存文件: {path}")
                    except (FileNotFoundError, PermissionError) as e:
                        logger.warning(f"无法删除文件 {path}: {e}")
            
            logger.info(f"缓存清理完成，当前缓存大小: {total_size / 1024 / 1024:.2f}MB")
            
            # 重新安排下一次清理
            self._schedule_cleanup()
        except Exception as e:
            logger.error(f"缓存清理过程中出错: {e}")
            # 即使出错也要重新安排清理
            self._schedule_cleanup()
    
    def get_cache_path(self, url, content_type=None):
        """根据URL和内容类型获取缓存路径"""
        # 使用URL的哈希值作为文件名，避免路径过长或包含非法字符
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # 根据内容类型选择缓存目录
        if content_type and "text/html" in content_type:
            cache_dir = self.html_cache_dir
            ext = ".html"
        elif content_type and ("image/" in content_type or "video/" in content_type or "audio/" in content_type):
            cache_dir = self.media_cache_dir
            # 从content_type中提取扩展名
            ext = "." + content_type.split("/")[-1].split(";")[0]
        else:
            cache_dir = self.response_cache_dir
            ext = ".dat"
        
        return os.path.join(cache_dir, url_hash + ext)
    
    def save_to_cache(self, url, content, content_type=None, headers=None):
        """保存响应内容到缓存"""
        # 如果缓存被全局禁用，直接返回
        if not self.cache_enabled:
            return False
            
        # 根据内容类型决定是否缓存
        if content_type:
            if "text/html" in content_type and not self.cache_html:
                return False
            elif ("image/" in content_type or "video/" in content_type or "audio/" in content_type) and not self.cache_media:
                return False
            elif not self.cache_other:
                return False
                
        # 检查文件大小，如果是大文件且未启用大文件缓存，则不缓存
        if len(content) > 1024 * 1024 and not self.cache_large_files:  # 大于1MB
            return False
            
        try:
            cache_path = self.get_cache_path(url, content_type)
            
            # 保存内容
            with open(cache_path, 'wb') as f:
                f.write(content)
            
            # 如果提供了headers，也保存它们
            if headers:
                headers_path = cache_path + ".headers"
                with open(headers_path, 'w', encoding='utf-8') as f:
                    json.dump(dict(headers), f)
            
            logger.debug(f"已缓存: {url} -> {cache_path}")
            return True
        except Exception as e:
            logger.warning(f"缓存保存失败 {url}: {e}")
            return False
    
    def get_from_cache(self, url, content_type=None):
        """从缓存获取响应内容"""
        # 如果缓存被全局禁用，直接返回None
        if not self.cache_enabled:
            return None, None
            
        # 根据内容类型决定是否使用缓存
        if content_type:
            if "text/html" in content_type and not self.cache_html:
                return None, None
            elif ("image/" in content_type or "video/" in content_type or "audio/" in content_type) and not self.cache_media:
                return None, None
            elif not self.cache_other:
                return None, None
                
        try:
            cache_path = self.get_cache_path(url, content_type)
            headers_path = cache_path + ".headers"
            
            # 检查缓存是否存在且未过期
            if not os.path.exists(cache_path):
                return None, None
            
            file_stat = os.stat(cache_path)
            if time.time() - file_stat.st_mtime > self.max_cache_age:
                # 缓存已过期，删除并返回None
                os.remove(cache_path)
                if os.path.exists(headers_path):
                    os.remove(headers_path)
                return None, None
            
            # 读取缓存内容
            with open(cache_path, 'rb') as f:
                content = f.read()
            
            # 读取headers（如果存在）
            headers = None
            if os.path.exists(headers_path):
                with open(headers_path, 'r', encoding='utf-8') as f:
                    headers = json.load(f)
            
            # 更新访问时间
            os.utime(cache_path, None)
            if os.path.exists(headers_path):
                os.utime(headers_path, None)
            
            logger.debug(f"缓存命中: {url}")
            return content, headers
        except Exception as e:
            logger.warning(f"读取缓存失败 {url}: {e}")
            return None, None
    
    def clear_cache(self, url=None, content_type=None):
        """清除特定URL的缓存或所有缓存"""
        if url:
            try:
                cache_path = self.get_cache_path(url, content_type)
                headers_path = cache_path + ".headers"
                
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                if os.path.exists(headers_path):
                    os.remove(headers_path)
                logger.debug(f"已清除缓存: {url}")
            except Exception as e:
                logger.warning(f"清除缓存失败 {url}: {e}")
        else:
            # 清除所有缓存
            clear_temp_cache()
            self._ensure_cache_dirs()
            logger.info("已清除所有缓存")

# 创建缓存管理器实例
cache_manager = CacheManager()

# 添加系统自检和缓存清理函数
def system_check_and_cleanup():
    """系统启动时的自检和缓存清理"""
    logger.info("开始系统自检和缓存清理...")
    
    # 1. 检查必要的目录是否存在，不存在则创建
    required_dirs = ["temp", "databases", "templates"]
    for dir_name in required_dirs:
        dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"创建目录: {dir_path}")
    
    # 2. 清除自身缓存
    # 清除临时文件夹
    clear_temp_cache()
    
    # 清除__pycache__文件夹
    pycache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__pycache__")
    if os.path.exists(pycache_dir):
        shutil.rmtree(pycache_dir)
        logger.info("清除 __pycache__ 目录")
    
    # 3. 检查配置文件完整性
    try:
        required_configs = ["SERVER", "DOMAIN", "PORT", "BIND_IP", "SCHEME", 
                           "LOGIN_PATH", "FAVICON_PATH", "INDEX_FILE", "LOGIN_FILE", "CHAT_FILE",
                           "FAVICON_FILE", "SESSION_COOKIE_NAME", "SERVER_NAME", "LOG_FILE"]
        missing_configs = [cfg for cfg in required_configs if cfg not in config]
        if missing_configs:
            logger.warning(f"配置文件缺少以下项: {', '.join(missing_configs)}")
    except Exception as e:
        logger.error(f"检查配置文件时出错: {e}")
    
    # 4. 初始化缓存目录结构
    cache_manager._ensure_cache_dirs()
    
    logger.info("系统自检和缓存清理完成")


def exit_confirmation():
    """退出程序时弹出确认对话框"""
    # 在Windows系统上使用tkinter创建图形化对话框
    if platform.system() == "Windows":
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # 创建隐藏的根窗口
            root = tk.Tk()
            root.withdraw()
            
            # 显示确认对话框
            result = messagebox.askyesno("退出确认", "是否退出程序？")
            root.destroy()
            return result
        except ImportError:
            # 如果tkinter不可用，回退到控制台输入
            pass
    
    # 非Windows系统或tkinter不可用时使用控制台输入
    print("\n检测到退出信号。是否退出程序？(y/N): ", end='', flush=True)
    response = sys.stdin.readline().strip().lower()
    return response == 'y'

def signal_handler(sig, frame):
    if exit_confirmation():
        logger.info("程序退出，正在清理缓存...")
        # 强制终止所有线程并退出
        os._exit(0)
    else:
        logger.info("继续运行程序。")

# 注册SIGINT信号处理器（Ctrl+C）
signal.signal(signal.SIGINT, signal_handler)

# 在Windows上使用更可靠的方法捕获窗口关闭事件
if platform.system() == "Windows":
    try:
        import ctypes
        
        # Windows API常量
        CTRL_CLOSE_EVENT = 2
        CTRL_C_EVENT = 0
        
        # 定义控制台处理函数类型
        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
        def console_ctrl_handler(ctrl_type):
            # 处理窗口关闭事件
            if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_C_EVENT):
                if exit_confirmation():
                    logger.info("程序退出，正在清理缓存...")
                    # 使用os._exit()强制终止进程
                    os._exit(0)
                else:
                    logger.info("继续运行程序")
                return 1
            return 0
        
        # 设置控制台控制处理器
        if ctypes.windll.kernel32.SetConsoleCtrlHandler(console_ctrl_handler, 1) == 0:
            logger.warning("无法设置控制台控制处理器")
    except (ImportError, AttributeError) as e:
        logger.warning(f"无法注册Windows控制台事件处理器: {e}")
        # 回退到使用SIGBREAK
        try:
            signal.signal(signal.SIGBREAK, signal_handler)
        except AttributeError:
            logger.warning("无法注册SIGBREAK信号处理器")

# ------------------ 会话与用户管理 ------------------
class Sessions(object):
    def __init__(self, length=64, age=604800, recycle_interval=3600):
        self.charset = string.ascii_letters + string.digits
        self.length = length
        self.age = age
        self.recycle_interval = recycle_interval
        self.sessions = list()
        self.session_cache = {}  # 添加会话缓存
        self.cache_ttl = 300  # 缓存有效期（秒）
        self.recycle_session()

    def generate_new_session(self):
        new_session = ''.join(random.choice(self.charset) for _ in range(self.length))
        current_time = time.time()
        self.sessions.append([new_session, current_time])
        # 添加到缓存
        self.session_cache[new_session] = current_time
        return new_session

    def is_session_exist(self, session):
        # 快速检查：无效会话直接返回False
        if not session:
            return False
            
        # 检查缓存 - 使用简单的字典查找，避免遍历
        if session in self.session_cache:
            return True
                
        # 缓存未命中，检查会话列表
        current_time = time.time()
        for _session in self.sessions:
            if _session[0] == session:
                # 更新缓存，但不频繁更新时间戳
                self.session_cache[session] = True
                # 只有当距离上次更新超过一定时间才更新时间戳
                if current_time - _session[1] > 300:  # 5分钟更新一次
                    _session[1] = current_time
                return True
                
        return False

    def recycle_session(self):
        now = time.time()
        deleting_sessions = [s for s in self.sessions if now - s[1] > self.age]
        for s in deleting_sessions:
            self.sessions.remove(s)
            # 同时清理缓存
            if s[0] in self.session_cache:
                del self.session_cache[s[0]]
                
        # 清理过期缓存
        expired_cache = [k for k, v in self.session_cache.items() if now - v > self.cache_ttl]
        for k in expired_cache:
            if k in self.session_cache:
                del self.session_cache[k]
                
        Timer(self.recycle_interval, self.recycle_session).start()

sessions = Sessions()

class Users(object):
    def __init__(self):
        self.users = users_data

    def is_effective_user(self, user_name, password):
        return user_name in self.users and password == self.users.get(user_name)

users = Users()

# ------------------ 模板管理 ------------------
class Template(object):
    def __init__(self):
        encoding = config.get("TEMPLATE_ENCODING", "utf-8")
        self.encoding = encoding
        self.template_dir = os.path.dirname(os.path.abspath(__file__))
        self.static_dir = os.path.join(self.template_dir, "static")
        
        # 确保静态资源目录存在
        if not os.path.exists(self.static_dir):
            os.makedirs(self.static_dir)
            logger.info(f"创建静态资源目录: {self.static_dir}")
        
        # 加载模板文件
        with open(config['INDEX_FILE'], encoding=encoding) as f:
            self.index_html = f.read()
        with open(config['LOGIN_FILE'], encoding=encoding) as f:
            self.login_html = f.read()
        # 添加加载chat.html的代码
        with open(config['CHAT_FILE'], encoding=encoding) as f:
            self.chat_html = f.read()

        # 加载404页面模板
        try:
            with open(config['NOT_FOUND_FILE'], encoding=encoding) as f:
                self.not_found_html = f.read()
        except FileNotFoundError:
            # 如果404页面文件不存在，创建一个简单的默认404页面
            self.not_found_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>404 - 页面未找到</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    h1 { font-size: 36px; color: #333; }
                    p { font-size: 18px; color: #666; }
                    a { color: #0066cc; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <h1>404 - 页面未找到</h1>
                <p>抱歉，您请求的页面不存在。</p>
                <p><a href="/">返回首页</a></p>
            </body>
            </html>
            """
            logger.warning(f"404页面文件 {config['NOT_FOUND_FILE']} 不存在，使用默认模板")
        
        # 编译正则表达式用于解析模板标签
        self.resource_pattern = re.compile(r'\{\{path:"([^"]+)",\s*filename:"([^"]+)"\}\}')
        
        # 添加更多模板标签的正则表达式
        self.var_pattern = re.compile(r'\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}')  # 变量: {{ variable }}
        self.if_pattern = re.compile(r'\{\%\s*if\s+(.+?)\s*\%\}(.*?)\{\%\s*endif\s*\%\}', re.DOTALL)  # 条件: {% if condition %}...{% endif %}
        self.if_else_pattern = re.compile(r'\{\%\s*if\s+(.+?)\s*\%\}(.*?)\{\%\s*else\s*\%\}(.*?)\{\%\s*endif\s*\%\}', re.DOTALL)  # 条件带else: {% if condition %}...{% else %}...{% endif %}
        self.for_pattern = re.compile(r'\{\%\s*for\s+([a-zA-Z0-9_]+)\s+in\s+([a-zA-Z0-9_\.]+)\s*\%\}(.*?)\{\%\s*endfor\s*\%\}', re.DOTALL)  # 循环: {% for item in items %}...{% endfor %}

    def _process_template(self, template_content, context=None):
        """处理模板内容，替换资源引用并应用上下文变量"""
        if context is None:
            context = {}
        
        # 替换资源引用
        def replace_resource(match):
            path_type = match.group(1)
            filename = match.group(2)
            
            # 根据路径类型构建URL
            if path_type == "static":
                return f"{config.get('SERVER', '')}/static/{filename}"
            elif path_type == "templates":
                return f"{config.get('SERVER', '')}/templates/{filename}"
            else:
                return f"{config.get('SERVER', '')}/{path_type}/{filename}"
        
        # 替换资源引用 - 修复正则表达式匹配和替换逻辑
        processed_content = self.resource_pattern.sub(replace_resource, template_content)
        
        # 添加更多的资源引用模式匹配
        # 处理 src="static/xxx" 格式
        processed_content = re.sub(r'src="static/([^"]+)"', 
                                  f'src="{config.get("SERVER", "")}/static/\\1"', 
                                  processed_content)
        
        # 处理 href="static/xxx" 格式
        processed_content = re.sub(r'href="static/([^"]+)"', 
                                  f'href="{config.get("SERVER", "")}/static/\\1"', 
                                  processed_content)
        
        # 处理 src="templates/xxx" 格式
        processed_content = re.sub(r'src="templates/([^"]+)"', 
                                  f'src="{config.get("SERVER", "")}/templates/\\1"', 
                                  processed_content)
        
        # 处理 href="templates/xxx" 格式
        processed_content = re.sub(r'href="templates/([^"]+)"', 
                                  f'href="{config.get("SERVER", "")}/templates/\\1"', 
                                  processed_content)
        
        # 处理 url(static/xxx) 格式 (CSS中的URL引用)
        processed_content = re.sub(r'url\([\'\"]?static/([^\'\"\)]+)[\'\"]?\)', 
                                  f'url({config.get("SERVER", "")}/static/\\1)', 
                                  processed_content)
        
        # 处理条件语句 (if-else)
        def process_if_else(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            else_content = match.group(3)
            
            # 评估条件
            try:
                # 安全地评估条件，只允许简单的比较和逻辑操作
                # 替换变量为实际值
                for var_name, var_value in context.items():
                    condition = condition.replace(var_name, repr(var_value))
                
                # 评估条件
                result = eval(condition, {"__builtins__": {}}, {})
                return self._process_template(if_content if result else else_content, context)
            except Exception as e:
                logger.error(f"条件评估错误: {e}, 条件: {condition}")
                return f"<!-- 条件评估错误: {condition} -->"
        
        # 处理条件语句 (if)
        def process_if(match):
            condition = match.group(1).strip()
            content = match.group(2)
            
            # 评估条件
            try:
                # 替换变量为实际值
                for var_name, var_value in context.items():
                    condition = condition.replace(var_name, repr(var_value))
                
                # 评估条件
                result = eval(condition, {"__builtins__": {}}, {})
                return self._process_template(content, context) if result else ""
            except Exception as e:
                logger.error(f"条件评估错误: {e}, 条件: {condition}")
                return f"<!-- 条件评估错误: {condition} -->"
        
        # 处理循环语句
        def process_for(match):
            var_name = match.group(1)
            collection_name = match.group(2)
            loop_content = match.group(3)
            
            # 获取集合
            collection = self._get_nested_value(context, collection_name)
            if not collection or not isinstance(collection, (list, tuple, dict)):
                return f"<!-- 循环错误: {collection_name} 不是有效的集合 -->"
            
            # 处理循环
            result = []
            for item in collection:
                # 创建新的上下文，包含循环变量
                loop_context = context.copy()
                loop_context[var_name] = item
                # 递归处理循环内容
                processed_loop = self._process_template(loop_content, loop_context)
                result.append(processed_loop)
            
            return "".join(result)
        
        # 应用模板处理
        processed_content = self.if_else_pattern.sub(process_if_else, processed_content)
        processed_content = self.if_pattern.sub(process_if, processed_content)
        processed_content = self.for_pattern.sub(process_for, processed_content)
        
        # 替换变量
        def replace_var(match):
            var_path = match.group(1)
            value = self._get_nested_value(context, var_path)
            return str(value) if value is not None else f"<!-- 未定义变量: {var_path} -->"
        
        processed_content = self.var_pattern.sub(replace_var, processed_content)
        
        # 替换简单的上下文变量 (向后兼容)
        for key, value in context.items():
            placeholder = '{' + key + '}'
            processed_content = processed_content.replace(placeholder, str(value))
        
        return processed_content
    
    def _get_nested_value(self, context, var_path):
        """获取嵌套字典中的值，支持点号访问，如 user.name"""
        parts = var_path.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        
        return value

    def get_login_html(self, login_failed=False, error_message=None):
        """获取处理后的登录页HTML"""
        try:
            # 准备上下文变量
            context = {
                'login_failed': '1' if login_failed else '0',
                'timestamp': str(int(time.time())),
                'server_name': config.get('SERVER_NAME', 'SilkRoad'),
                'error_message': error_message if error_message else '' # 添加错误消息
            }
            
            return self._process_template(self.login_html, context)
            
        except Exception as e:
            # 如果格式化失败，记录错误并返回原始模板
            logger.error(f"登录页面格式化错误: {e}")
            # 返回一个包含错误信息的简单HTML，或者原始模板
            # return f"<html><body>Login page error: {e}</body></html>"
            return self.login_html # 保持返回原始模板，避免因格式化失败导致无法登录

    def get_index_html(self, context=None):
        """获取处理后的首页HTML"""
        if context is None:
            context = {}
        return self._process_template(self.index_html, context)
        
    def get_chat_html(self, context=None):
        """获取处理后的聊天页HTML"""
        if context is None:
            context = {}
        return self._process_template(self.chat_html, context)
    
    def get_not_found_html(self, context=None):
        """获取处理后的404页面HTML"""
        if context is None:
            context = {
                'timestamp': str(int(time.time())),
                'server_name': config.get('SERVER_NAME', 'SilkRoad'),
                'requested_url': ''
            }
        return self._process_template(self.not_found_html, context)

    def render_template(self, template_name, context=None):
        """渲染指定的模板文件"""
        if context is None:
            context = {}
        
        template_path = os.path.join(self.template_dir, "templates", template_name)
        if not os.path.exists(template_path):
            logger.error(f"模板文件不存在: {template_path}")
            return f"<!-- 模板文件不存在: {template_name} -->"
        
        try:
            with open(template_path, encoding=self.encoding) as f:
                template_content = f.read()
            return self._process_template(template_content, context)
        except Exception as e:
            logger.error(f"渲染模板 {template_name} 失败: {e}")
            return f"<!-- 渲染模板失败: {template_name}, 错误: {e} -->"
    
    def get_static_file(self, filename):
        """获取静态文件内容"""
        file_path = os.path.join(self.static_dir, filename)
        if not os.path.exists(file_path):
            return None, None
        
        # 根据文件扩展名确定内容类型
        content_type = self._get_content_type(filename)
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return content, content_type
        except Exception as e:
            logger.error(f"读取静态文件失败 {filename}: {e}")
            return None, None
    
    def _get_content_type(self, filename):
        """根据文件扩展名确定内容类型"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.otf': 'font/otf',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
        }
        return content_types.get(ext, 'application/octet-stream')

template = Template()

# ------------------ 浏览器信息伪装 ------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

# ------------------ 代理处理 ------------------
class Proxy(object):
    def __init__(self, handler):
        self.handler = handler
        # 从请求路径中提取目标 URL
        path = self.handler.path
        
        # 处理没有协议的URL（如 /www.baidu.com/favicon.ico）
        if path.startswith('/'):
            if path[1:].startswith('http://') or path[1:].startswith('https://'):
                # 正常的代理URL格式：/http://... 或 /https://...
                self.url = path[1:]
            elif path.startswith('/http') and not path.startswith('/http://') and not path.startswith('/https://'):
                # 处理可能的错误格式，如 /https:/www.baidu.com
                self.url = path[1:].replace(':/','://')
            elif path[1:].startswith('www.') and '.' in path[1:].split('/')[0]:
                # 没有协议的域名URL，添加https://
                self.url = 'https://' + path[1:]
            else:
                # 相对路径或其他格式，标记为无效URL
                self.url = path
                self.is_valid_url = False
                return
        else:
            self.url = path
        
        # 标记为有效URL
        self.is_valid_url = True
        
        try:
            parse_result = parse.urlparse(self.url)
            self.scheme = parse_result.scheme
            self.netloc = parse_result.netloc
            self.site = self.scheme + '://' + self.netloc if self.scheme and self.netloc else ''
            self.path = parse_result.path
        except Exception as e:
            logger.error(f"URL解析错误: {self.url}, 错误: {str(e)}")
            self.is_valid_url = False
            return
            
        # 定义无效请求头列表，这些请求头会被过滤掉
        self.invalid_headers = {
            "cf-connecting-ip", "x-forwarded-for", "x-real-ip",
            "true-client-ip", "x-vercel-deployment-url", "x-vercel-forwarded-for",
            "x-forwarded-host", "x-forwarded-port", "x-forwarded-proto",
            "x-vercel-id", "baggage", "cdn-loop", "cf-ray", "cf-visitor",
            "cf-ipcountry", "cf-worker", "x-amzn-trace-id", "x-cache"
        }
        # 设置重试次数和超时时间
        self.max_retries = 3
        self.timeout = 30.0

    def proxy(self):
        # 判断是否为 WebSocket 请求，若是则调用占位处理
        if self.handler.headers.get('Upgrade', '').lower() == 'websocket':
            self.process_websocket()
            return

        # 检查URL是否有效
        if not hasattr(self, 'is_valid_url') or not self.is_valid_url:
            self.process_error(f"unknown url type: '{self.handler.path}'")
            return

        self.process_request()
        content_length = int(self.handler.headers.get('Content-Length', 0))
        data = self.handler.rfile.read(content_length) if content_length > 0 else None
        # 只对GET请求尝试使用缓存，且缓存必须启用
        if self.handler.command == 'GET' and cache_manager.cache_enabled:
            # 尝试从缓存获取响应
            cached_content, cached_headers = cache_manager.get_from_cache(self.url)
            if cached_content is not None:
                logger.info(f"使用缓存响应: {self.url}")
                # 模拟一个响应对象
                class CachedResponse:
                    def __init__(self, content, headers):
                        self.content = content
                        self.headers = headers or {}
                        self.status_code = 200
                        self.encoding = 'utf-8'
                    
                    def iter_bytes(self, chunk_size):
                        """模拟iter_bytes方法，用于分块传输"""
                        remaining = self.content
                        while remaining:
                            chunk, remaining = remaining[:chunk_size], remaining[chunk_size:]
                            yield chunk
                
                # 使用缓存的内容处理响应
                self.process_response(CachedResponse(cached_content, cached_headers))
                return
        # 添加重试逻辑
        retry_count = 0
        # 从连接池获取客户端
        client = http_client_pool.get_client()
        try:
            while retry_count < self.max_retries:
                try:
                    # 复制所有请求头，并随机设置 User-Agent 以伪装客户端信息
                    headers = {}
                    for k, v in self.handler.headers.items():
                        if k.lower() not in self.invalid_headers:
                           headers[k] = v
                    if config.get("RANDOM_UA_ENABLED", True):
                        headers['User-Agent'] = random.choice(USER_AGENTS)
                    
                    # 使用连接池中的客户端发送请求
                    r = client.request(method=self.handler.command, url=self.url, headers=headers, content=data)
                    # 如果请求成功，处理响应并退出重试循环
                    self.process_response(r)
                    break
                except ssl.SSLError as ssl_error:
                    # 特别处理 SSL 错误
                    logger.warning(f"SSL Error on attempt {retry_count+1}/{self.max_retries}: {ssl_error}")
                    if "EOF occurred in violation of protocol" in str(ssl_error) and retry_count < self.max_retries - 1:
                        retry_count += 1
                        time.sleep(1)  # 短暂延迟后重试
                        continue
                    else:
                        self.process_error(f"SSL Error: {ssl_error}")
                        break
                except httpx.TimeoutException as timeout_error:
                    # 处理超时错误
                    logger.warning(f"Timeout on attempt {retry_count+1}/{self.max_retries}: {timeout_error}")
                    if retry_count < self.max_retries - 1:
                        retry_count += 1
                        time.sleep(1)
                        continue
                    else:
                        self.process_error(f"Request timed out after {self.max_retries} attempts")
                        break
                except Exception as error:
                    # 处理其他错误，添加更多上下文信息
                    error_context = {
                        "url": self.url,
                        "method": self.handler.command,
                        "headers": str(headers)[:200] + "..." if len(str(headers)) > 200 else str(headers),
                        "retry_count": retry_count
                    }
                    logger.error(f"Error on attempt {retry_count+1}/{self.max_retries}: {error}, Context: {error_context}")
                    self.process_error(f"请求错误: {error}")
                    break
        finally:
            # 请求完成后，将客户端归还到连接池
            http_client_pool.release_client(client)

    def process_websocket(self):
        # 占位处理：后续可结合 websockets 库实现双向持续连接
        self.handler.send_error(HTTPStatus.NOT_IMPLEMENTED, "WebSocket代理尚未实现")
        logger.warning("WebSocket请求未实现：{}", self.url)

    def process_request(self):
        # 根据客户端 Connection 头判断是否启用 keep-alive
        client_conn = self.handler.headers.get('Connection', '').lower()
        conn_value = 'keep-alive' if client_conn == 'keep-alive' else 'close'
        # 修改部分请求头以突破检测与格式化
        self.modify_request_header('Referer', lambda x: x.replace(config['SERVER'], ''))
        self.modify_request_header('Origin', self.site)
        self.modify_request_header('Host', self.netloc)
        # 保留或添加 Accept-Language、Cache-Control 等常见头（示例，可扩展）
        if 'Accept-Language' not in self.handler.headers:
            self.handler.headers.add_header('Accept-Language', 'zh-CN,cn;q=0.9')
        self.modify_request_header('Accept-Encoding', 'identity')
        self.modify_request_header('Connection', conn_value)
        # 如果存在 Range 请求头，保持不变（用于断点续传）

    def process_response(self, r):
        # 获取内容类型和URL
        content_type = r.headers.get('Content-Type', '')
        url = self.url
        
        # 检查是否可缓存
        cacheable = r.status_code == 200 and self.handler.command == 'GET' and cache_manager.cache_enabled
        
        # 判断是否为流媒体内容
        is_stream_media = any(media_type in content_type.lower() for media_type in ['video/', 'audio/', 'application/octet-stream'])
        is_large_file = int(r.headers.get('Content-Length', 0)) > 1024 * 1024  # 大于1MB
        
        # 发送响应头
        self.handler.send_response(r.status_code)
        
        # 转发必要的响应头
        if "Content-Range" in r.headers:
            self.handler.send_header("Content-Range", r.headers["Content-Range"])
        if "location" in r.headers:
            self.handler.send_header('Location', self.revision_location(r.headers['location']))
        if "content-type" in r.headers:
            # 对于HTML内容，强制使用UTF-8，防止乱码
            if "text/html" in r.headers['content-type']:
                 self.handler.send_header('Content-Type', "text/html; charset=utf-8")
            else:
                 self.handler.send_header('Content-Type', r.headers['content-type'])
        if "set-cookie" in r.headers:
            self.revision_set_cookie(r.headers['set-cookie'])
        
        # 根据客户端请求决定连接是否保持
        client_conn = self.handler.headers.get('Connection', '').lower()
        conn_value = 'keep-alive' if client_conn == 'keep-alive' and config.get("ENABLE_KEEP_ALIVE", True) else 'close'
        self.handler.send_header('Connection', conn_value)
        
        # 如果使用keep-alive，添加Keep-Alive头部
        if conn_value == 'keep-alive':
            self.handler.send_header('Keep-Alive', 'timeout=60, max=100')
            
        self.handler.send_header('Access-Control-Allow-Origin', '*')
        
        # 对于流媒体或大文件使用分块传输
        if is_stream_media or is_large_file:
            # 使用分块传输编码
            self.handler.send_header('Transfer-Encoding', 'chunked')
            self.handler.end_headers()
            
            # 创建缓冲队列和预加载线程
            buffer_queue = queue.Queue(maxsize=50)  # 最多预加载50个块
            t = threading.Thread(
                target=preload_streamed_response_content_async,
                args=(r, buffer_queue, 8192),  # 8KB 的块大小
                daemon=True
            )
            t.start()
            
            # 流式传输内容
            try:
                while True:
                    try:
                        chunk = buffer_queue.get(timeout=15)
                        buffer_queue.task_done()
                        
                        if chunk is None:  # 结束标记
                            break
                            
                        # 写入分块大小（十六进制）
                        self.handler.wfile.write(f"{len(chunk):X}\r\n".encode('ascii'))
                        # 写入数据块
                        self.handler.wfile.write(chunk)
                        self.handler.wfile.write(b"\r\n")
                        
                    except queue.Empty:
                        logger.warning("获取流内容超时")
                        break
                
                # 写入结束块
                self.handler.wfile.write(b"0\r\n\r\n")
                
                # 如果可缓存且启用了媒体缓存，尝试缓存内容
                if cacheable and is_stream_media and cache_manager.cache_media and not is_large_file:
                    # 这里可以实现媒体内容的缓存逻辑
                    pass
                    
            except Exception as e:
                logger.error(f"流式传输内容时出错: {e}")
        else:
            # 对于普通内容，使用标准处理方式
            if "text/html" in content_type:
                # 尝试使用响应头中的编码，如果失败则回退
                try:
                    encoding = r.encoding or 'utf-8'
                    content = self.revision_link(r.content, encoding)
                except Exception:
                    # 如果指定的编码失败，尝试使用 utf-8 忽略错误
                    content = self.revision_link(r.content, 'utf-8')
                
                # 更新内容长度
                content_length = len(content)
                self.handler.send_header('Content-Length', content_length)
                self.handler.end_headers()
                self.handler.wfile.write(content)
                
                # 缓存HTML内容
                if cacheable and cache_manager.cache_html:
                    cache_manager.save_to_cache(url, content, "text/html; charset=utf-8", r.headers)
            else:
                # 对于其他非HTML内容
                content = r.content
                content_length = len(content)
                self.handler.send_header('Content-Length', content_length)
                self.handler.end_headers()
                self.handler.wfile.write(content)
                
                # 缓存其他内容
                if cacheable and cache_manager.cache_other and not is_large_file:
                    cache_manager.save_to_cache(url, content, content_type, r.headers)

    def process_error(self, error):
        """处理代理请求错误"""
        # 对于404错误，使用自定义404页面
        if "404" in str(error) or "Not Found" in str(error):
            # 去掉URL开头的斜杠
            requested_url = self.url
            if requested_url.startswith('/'):
                requested_url = requested_url[1:]
                
            context = {
                'requested_url': requested_url,
                'error_message': str(error)
            }
            body = template.get_not_found_html(context)
            self.handler.send_response(HTTPStatus.NOT_FOUND)
            encoded = body.encode(config.get("TEMPLATE_ENCODING", "utf-8"))
            self.handler.send_header('Content-Length', len(encoded))
            self.handler.send_header('Content-Type', 'text/html; charset={}'.format(config.get("TEMPLATE_ENCODING", "utf-8")))
            self.handler.end_headers()
            self.handler.wfile.write(encoded)
        else:
            # 确保错误消息只包含ASCII字符，避免编码错误
            try:
                error_message = str(error).encode('ascii', errors='ignore').decode('ascii')
            except:
                error_message = "Request processing error"
            self.handler.send_error(HTTPStatus.BAD_REQUEST, error_message)
        logger.error("Proxy error: {}", error)

    def modify_request_header(self, header, value):
        target_header = None
        for _header in self.handler.headers._headers:
            if _header[0].lower() == header.lower():
                target_header = _header
                break
        if target_header is not None:
            self.handler.headers._headers.remove(target_header)
            new_value = value(target_header[1]) if callable(value) else value
            self.handler.headers._headers.append((header, new_value))
    
    def is_valid_cookie(self, cookie):
        """判断Cookie是否有效"""
        # 过滤掉空Cookie或只包含空格的Cookie
        if not cookie or cookie.strip() == "":
            return False
        
        # 过滤掉不包含等号的Cookie（无效格式）
        if "=" not in cookie:
            return False
            
        # 过滤掉某些特定的Cookie（如有需要）
        # 例如：if cookie.startswith("__Host-"):
        #          return False
        
        return True

    def revision_set_cookie(self, cookies):
        """使用正则表达式处理Set-Cookie头"""
        cookie_regex = re.compile(r'([^,;]+(?:; [^,;]+)*)(?:, |$)')
        for cookie_match in cookie_regex.finditer(cookies):
            cookie = cookie_match.group(1)
            # 过滤无效的 Cookie
            if self.is_valid_cookie(cookie):
                self.handler.send_header('Set-Cookie', self.revision_response_cookie(cookie))
    
    def revision_response_cookie(self, cookie):
        """使用正则表达式修改Cookie属性"""
        # 设置24小时过期
        expires_time = (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 使用正则表达式替换或添加expires属性
        if re.search(r'expires=[^,;]+', cookie, re.IGNORECASE):
            cookie = re.sub(r'expires=[^,;]+', f'expires={expires_time}', cookie, flags=re.IGNORECASE)
        else:
            cookie += f'; expires={expires_time}'
        
        # 替换domain属性
        if re.search(r'domain=[^,;]+', cookie, re.IGNORECASE):
            cookie = re.sub(r'domain=[^,;]+', f'domain=.{config["DOMAIN"]}', cookie, flags=re.IGNORECASE)
        
        # 替换path属性
        if re.search(r'path=/', cookie, re.IGNORECASE):
            cookie = re.sub(r'path=/', f'path=/{self.site}', cookie, flags=re.IGNORECASE)
        
        # 如果使用HTTP协议，移除secure属性
        if config['SCHEME'] == 'http':
            cookie = re.sub(r'secure;?', '', cookie, flags=re.IGNORECASE)
        
        return cookie

    def revision_location(self, location):
        """
        【已修改】使用 urllib.parse.urljoin 修正重定向链接，更健壮、更简单。
        添加检查逻辑，避免重复添加代理前缀，解决循环重定向问题。
        """
        # self.url 是原始请求的完整URL, location是Location头的值
        # urljoin 会正确处理绝对路径(`/path`)、相对路径(`sub/page`)和完整URL(`http://...`)
        new_target_url = parse.urljoin(self.url, location)
        
        # 拼接代理前缀
        proxy_server = config['SERVER'].rstrip('/')
        
        # 检查是否已经包含代理前缀，避免重复添加
        proxy_pattern = re.escape(proxy_server) + r'/https?://'
        if re.match(proxy_pattern, new_target_url):
            # 已经包含代理前缀，直接返回
            return new_target_url
        
        # 检查是否是重定向到自身，这可能导致循环重定向
        if new_target_url == self.url:
            # 如果重定向到自身，直接返回原始URL加代理前缀
            return f"{proxy_server}/{new_target_url}"
        
        # 正常情况，添加代理前缀
        return f"{proxy_server}/{new_target_url}"

    def revision_link(self, body, coding):
        if not coding:
            return body

        try:
            content_str = body.decode(coding, errors='ignore')
        except (UnicodeDecodeError, TypeError):
            logger.warning(f"无法使用编码 {coding} 解码内容，将返回原始数据。 URL: {self.url}")
            return body

        # 代理服务器地址，确保末尾没有斜杠
        proxy_prefix = config['SERVER'].rstrip('/')
        # 当前请求的URL，作为解析相对路径的基准
        base_url = self.url
        # 目标网站的域名 (e.g., "www.google.com")
        target_netloc = self.netloc

        def rewrite_url_if_internal(url):
            """辅助函数：检查URL并重写。现在同时处理内部链接和外部链接。"""
            # 忽略空链接和特殊协议链接
            if not url or url.startswith(('javascript:', 'mailto:', '#', 'data:')):
                return url

            # 使用 urljoin 将各种URL（相对、绝对）转换为完整的绝对URL
            absolute_url = parse.urljoin(base_url, url)
            
            # 检查解析后的URL是否属于当前代理的目标域
            try:
                parsed_absolute_url = parse.urlparse(absolute_url)
                if parsed_absolute_url.netloc == target_netloc:
                    # 是内部链接，添加代理前缀
                    return f"{proxy_prefix}/{absolute_url}"
                elif parsed_absolute_url.netloc and parsed_absolute_url.scheme in ('http', 'https'):
                    # 是外部链接，也添加代理前缀
                    return f"{proxy_prefix}/{absolute_url}"
            except Exception as e:
                logger.warning(f"URL解析失败: {absolute_url}, 错误: {e}")
                pass

            # 默认返回原始URL（特殊链接或解析失败的链接）
            return url

        # 1. 重写HTML中常见的链接属性 (href, src, action, etc.)
        def rewrite_html_attr(match):
            attr, quote, url = match.groups()
            rewritten_url = rewrite_url_if_internal(url)
            return f'{attr}={quote}{rewritten_url}{quote}'
        
        # 匹配 <a href="...">, <img src="..."> 等
        link_pattern = re.compile(r"""\b(href|src|action|data-src|formaction|background|poster)\s*=\s*(['"])(.*?)\2""", re.IGNORECASE | re.DOTALL)
        content_str = link_pattern.sub(rewrite_html_attr, content_str)

        # 2. 特殊处理 srcset 属性 (用于响应式图片)
        def rewrite_srcset_attr(match):
            attr, quote, srcset_value = match.groups()
            if not srcset_value:
                return match.group(0)
            
            # srcset 是由逗号分隔的 "url descriptor" 列表
            parts = srcset_value.split(',')
            rewritten_parts = []
            for part in parts:
                part = part.strip()
                # 分离 URL 和描述符 (e.g., "image.jpg 1x")
                url_match = re.match(r'(\S+)\s*(.*)', part)
                if url_match:
                    url, descriptor = url_match.groups()
                    rewritten_url = rewrite_url_if_internal(url)
                    rewritten_parts.append(f'{rewritten_url} {descriptor}'.strip())
            
            rewritten_srcset = ', '.join(rewritten_parts)
            return f'{attr}={quote}{rewritten_srcset}{quote}'

        srcset_pattern = re.compile(r"""\b(srcset)\s*=\s*(['"])(.*?)\2""", re.IGNORECASE | re.DOTALL)
        content_str = srcset_pattern.sub(rewrite_srcset_attr, content_str)

        # 3. 重写CSS中的 url(...)
        def rewrite_css_url(match):
            quote, url = match.groups()
            rewritten_url = rewrite_url_if_internal(url)
            return f'url({quote}{rewritten_url}{quote})'
            
        css_url_pattern = re.compile(r"""url\((['"]?)(.*?)\1\)""", re.IGNORECASE)
        content_str = css_url_pattern.sub(rewrite_css_url, content_str)
        
        # 在</body>标签前插入自定义JS脚本
        if "</body>" in content_str:
            scripts = script_manager.get_all_scripts()
            if scripts:
                script_tags = "\n<!-- Custom JS Scripts Start -->\n"
                for script_name, script_content in scripts.items():
                    script_tags += f"<script>/* {script_name} */\n{script_content}\n</script>\n"
                script_tags += "<!-- Custom JS Scripts End -->\n"
                content_str = content_str.replace("</body>", f"{script_tags}</body>", 1)

        return content_str.encode('utf-8')

# ------------------ HTTP 请求处理 ------------------
class SilkRoadHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # 支持持久连接
    timeout = 60  # 设置连接超时时间，单位秒

    def __init__(self, request, client_address, server):
        self.login_path = config['LOGIN_PATH']
        self.favicon_path = config['FAVICON_PATH']
        self.server_name = config['SERVER_NAME']
        self.session_cookie_name = config['SESSION_COOKIE_NAME']
        self.domain_re = re.compile(r'(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+')        
        self.keep_alive = True  # 默认启用持久连接
        with open(config['FAVICON_FILE'], 'rb') as f:
            self.favicon_data = f.read()
        super().__init__(request, client_address, server)

    def handle_one_request(self):
        """处理单个请求，支持持久连接"""
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                # 请求解析失败
                return
            
            # 检查Connection头，决定是否保持连接
            conn_header = self.headers.get('Connection', '').lower()
            self.keep_alive = conn_header == 'keep-alive'
            
            # 处理请求
            self.do_request()
            self.wfile.flush()
            
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            # 客户端断开连接，记录日志并关闭连接
            logger.debug(f"客户端断开连接: {e}")
            self.close_connection = True
        except socket.timeout as e:
            # 连接超时，记录日志并关闭连接
            logger.debug(f"连接超时: {e}")
            self.close_connection = True
        except Exception as e:
            logger.error(f"处理请求时出错: {e}")
            self.close_connection = True

    def do_GET(self):
        self.do_request()

    def do_POST(self):
        self.do_request()

    def do_HEAD(self):
        self.do_request()
    
    def do_request(self):
        """处理所有请求的核心逻辑"""
        # 减少日志记录频率，只记录关键信息
        if random.random() < 0.1:  # 只记录10%的请求，减少日志开销
            logger.info(f"{self.command} Request: {self.path} from {self.client_address}")

        # 快速路径检查 - 直接检查常见路径模式，避免不必要的解析
        if self.path == self.login_path or self.path == self.login_path + '/':
            self.process_login()
            return
        elif self.path == self.favicon_path:
            self.return_favicon()
            return
        elif self.path == '/':
            self.process_index()
            return
        elif self.path == '/chat' or self.path == '/chat/':
            self.process_chat()
            return
        elif self.path.startswith('/static/'):
            self.process_static_file()
            return
        elif self.path.startswith('/templates/'):
            self.process_template_file()
            return

        # 检查是否需要登录验证 - 如果配置禁用了登录验证，跳过验证
        if not config.get("LOGIN_VERIFICATION_ENABLED", True):
            # 直接检查是否是代理请求，避免解析URL
            if self.path[1:].startswith('http://') or self.path[1:].startswith('https://'):
                # 检查是否包含重复的代理URL
                proxy_url = self.path[1:]
                proxy_match = re.match(r'https?://[^/]+/(https?://.+)', proxy_url)
                if proxy_match:
                    # 如果包含重复代理URL，则去掉外层代理
                    self.path = '/' + proxy_match.group(1)
                    logger.debug(f"Removed duplicate proxy prefix, new path: {self.path}")
                
                Proxy(self).proxy()
                return
                
            # 解析查询参数，检查是否有url参数
            parsed_url = parse.urlparse(self.path)
            query_params = parse.parse_qs(parsed_url.query)
            
            if 'url' in query_params:
                target_url = query_params['url'][0]
                original_path = self.path
                if not target_url.startswith(('http://', 'https://')):
                    if target_url.startswith('//'):
                        target_url = 'https:' + target_url
                    else:
                        target_url = 'https://' + target_url
                self.path = '/' + target_url
                try:
                    Proxy(self).proxy()
                finally:
                    self.path = original_path
                return
                
            # 如果不是代理请求，处理本地资源
            self.process_not_found()
            return

        # 需要登录验证 - 检查会话
        session = self.get_request_cookie(self.session_cookie_name)
        if sessions.is_session_exist(session):
            # 直接检查是否是代理请求，避免解析URL
            if self.path[1:].startswith('http://') or self.path[1:].startswith('https://'):
                # 检查是否包含重复的代理URL
                proxy_url = self.path[1:]
                proxy_match = re.match(r'https?://[^/]+/(https?://.+)', proxy_url)
                if proxy_match:
                    # 如果包含重复代理URL，则去掉外层代理
                    self.path = '/' + proxy_match.group(1)
                    logger.debug(f"Removed duplicate proxy prefix, new path: {self.path}")
                
                Proxy(self).proxy()
                return
                
            # 解析查询参数，检查是否有url参数
            parsed_url = parse.urlparse(self.path)
            query_params = parse.parse_qs(parsed_url.query)
            
            if 'url' in query_params:
                target_url = query_params['url'][0]
                original_path = self.path
                if not target_url.startswith(('http://', 'https://')):
                    if target_url.startswith('//'):
                        target_url = 'https:' + target_url
                    else:
                        target_url = 'https://' + target_url
                self.path = '/' + target_url
                try:
                    Proxy(self).proxy()
                finally:
                    self.path = original_path
                return
                
            # 如果不是代理请求，处理本地资源
            self.process_not_found()
        else:
            # 未登录，重定向到登录页
            self.redirect_to_login()
            
    def _process_authenticated_request(self, parsed_path, query_params, parsed_url):
        """处理已通过身份验证的请求"""
        # 优先检查是否存在 'url' 查询参数
        if 'url' in query_params:
            target_url = query_params['url'][0] # Get the target URL
            logger.debug(f"Found 'url' parameter: '{target_url}'. Processing as proxy request.")
            # Modify self.path temporarily for the Proxy class to work correctly
            original_path = self.path
            
            # 检查target_url是否已经包含代理URL，如果有则先去掉
            proxy_match = re.match(r'https?://[^/]+/(https?://.+)', target_url)
            if proxy_match:
                target_url = proxy_match.group(1)
                logger.debug(f"Removed proxy prefix from URL, new target: {target_url}")
            
            # Ensure the target URL starts with a scheme, add https if missing (common case)
            if not target_url.startswith(('http://', 'https://')):
                 # Basic check, might need refinement for //domain cases
                 if target_url.startswith('//'):
                     target_url = 'https:' + target_url # Assume https
                 else:
                     target_url = 'https://' + target_url # Assume https

            self.path = '/' + target_url # Prepend '/' as Proxy expects
            try:
                Proxy(self).proxy() # Call proxy logic with modified path
            finally:
                self.path = original_path # Restore original path
        # 如果没有 'url' 参数，再执行原来的判断逻辑 (基于路径 like /http://...)
        elif self.path[1:].startswith('http://') or self.path[1:].startswith('https://'):
            logger.debug("Request needs proxy based on path structure (direct check).")
            Proxy(self).proxy() # 执行代理逻辑
        else:
            logger.debug("Request does not need proxy. Processing original.")
            self.process_original() # 处理本地资源或特殊路径

    def is_login(self):
        # 如果登录验证被禁用，直接返回True
        if not config.get("LOGIN_VERIFICATION_ENABLED", True):
            return True
            
        # 登录页面与 favicon 均无需验证会话
        parsed_url = parse.urlparse(self.path)
        parsed_path = parsed_url.path.rstrip('/') or '/'
        norm_login_path = self.login_path.rstrip('/')
        norm_favicon_path = self.favicon_path.rstrip('/')
        
        if parsed_path == norm_login_path or parsed_path == norm_favicon_path:
            return True
            
        # 获取会话Cookie
        session = self.get_request_cookie(self.session_cookie_name)
        
        # 使用优化后的会话验证方法
        return sessions.is_session_exist(session)

    def process_original(self):
        if self.path == self.favicon_path:
            self.process_favicon()
        elif self.path == self.login_path:
            self.process_login()
        elif self.path == '/chat':  # 添加对/chat路径的处理
            self.process_chat()
        elif self.path.startswith('/static/'):  # 处理静态资源请求
            self.process_static_file()
        elif self.path.startswith('/templates/'):  # 处理模板资源请求
            self.process_template_file()
        else:
            if self.path == '/':
                self.process_index()
            else:
                # 返回404页面
                self.process_not_found()
    
    def process_login(self):
        # 保持之前的 process_login 修改，特别是 GET 请求部分
        if self.command == 'POST':
            # ... existing POST handling code ...
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length).decode('utf-8')
            # 尝试更健壮地解析 POST 数据
            try:
                parsed_data = parse.parse_qs(parse.unquote(raw_data))
                user = parsed_data.get('user', [None])[0]
                password = parsed_data.get('password', [None])[0]

                if user and password and users.is_effective_user(user, password):
                    session = sessions.generate_new_session()
                    self.send_response(HTTPStatus.FOUND)
                    self.send_header('Location', '/') # 登录成功后重定向到根目录
                    expires = (datetime.datetime.now() + datetime.timedelta(hours=24)).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
                    self.send_header('Set-Cookie',
                                     '{}={}; expires={}; path=/; HttpOnly'
                                     .format(self.session_cookie_name, session, expires))
                    self.end_headers()
                    logger.info(f"User '{user}' logged in successfully.")
                    return 
                else:
                     logger.warning(f"Login failed for user '{user}'. Invalid credentials or missing data.")
                     body = template.get_login_html(login_failed=True)
                     self.return_html(body) # 返回登录页并提示失败

            except Exception as e:
                 logger.error(f"Error processing login POST data: {e}. Raw data: {raw_data}")
                 # 即使解析出错，也返回登录页面，避免卡住
                 body = template.get_login_html(login_failed=True, error_message="登录请求处理失败")
                 self.return_html(body, status_code=HTTPStatus.BAD_REQUEST)


        else: # GET request
            session = self.get_request_cookie(self.session_cookie_name)
            if sessions.is_session_exist(session):
                logger.debug("Logged-in user accessed login page, redirecting to root.")
                self.send_response(HTTPStatus.FOUND)
                self.send_header('Location', '/')
                self.end_headers()
            else:
                logger.debug("Serving login page to non-logged-in user.")
                body = template.get_login_html(login_failed=False)
                self.return_html(body) # 确保这里返回 200 OK

    def process_index(self):
        body = template.get_index_html()
        self.return_html(body)

    def process_chat(self):
        body = template.get_chat_html()
        self.return_html(body)

    def process_not_found(self):
        """处理404页面请求"""
        # 去掉URL开头的斜杠
        requested_url = self.path
        if requested_url.startswith('/'):
            requested_url = requested_url[1:]
            
        context = {
            'requested_url': requested_url,
            'timestamp': str(int(time.time())),
            'server_name': self.server_name
        }
        body = template.get_not_found_html(context)
        self.send_response(HTTPStatus.NOT_FOUND)
        encoded = body.encode(config.get("TEMPLATE_ENCODING", "utf-8"))
        self.send_header('Content-Length', len(encoded))
        self.send_header('Content-Type', 'text/html; charset={}'.format(config.get("TEMPLATE_ENCODING", "utf-8")))
        self.end_headers()
        self.wfile.write(encoded)
        logger.info(f"返回404页面: {self.path}")

    def process_static_file(self):
        """处理静态资源文件请求"""
        try:
            # 从路径中提取文件名
            filename = self.path[8:]  # 去掉 '/static/' 前缀
            
            # 确保文件名不包含路径遍历攻击
            if '..' in filename or filename.startswith('/'):
                self.send_error(HTTPStatus.FORBIDDEN, "非法的文件路径")
                return
            
            # 构建静态文件路径
            file_path = os.path.join(template.static_dir, filename)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self.send_error(HTTPStatus.NOT_FOUND, "静态文件未找到")
                logger.warning(f"静态文件未找到: {file_path}")
                return
            
            # 确定内容类型
            content_type = template._get_content_type(filename)
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 发送文件内容
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Cache-Control', 'max-age=86400')  # 缓存1天
            self.end_headers()
            self.wfile.write(content)
            logger.debug(f"成功提供静态文件: {filename}")
        except Exception as e:
            logger.error(f"处理静态文件失败 {self.path}: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "处理静态文件失败")
    
    def process_template_file(self):
        """处理模板资源文件请求"""
        try:
            # 从路径中提取文件名
            filename = self.path[11:]  # 去掉 '/templates/' 前缀
            
            # 确保文件名不包含路径遍历攻击
            if '..' in filename or filename.startswith('/'):
                self.send_error(HTTPStatus.FORBIDDEN, "非法的文件路径")
                return
            
            # 构建模板文件路径
            templates_dir = os.path.join(template.template_dir, "templates")
            if not os.path.exists(templates_dir):
                os.makedirs(templates_dir)
                logger.info(f"创建模板目录: {templates_dir}")
            
            file_path = os.path.join(templates_dir, filename)
            
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self.send_error(HTTPStatus.NOT_FOUND, "模板文件未找到")
                logger.warning(f"模板文件未找到: {file_path}")
                return
            
            # 确定内容类型
            content_type = template._get_content_type(filename)
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 发送文件内容
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Cache-Control', 'max-age=86400')  # 缓存1天
            self.end_headers()
            self.wfile.write(content)
            logger.debug(f"成功提供模板文件: {filename}")
        except Exception as e:
            logger.error(f"处理模板文件失败 {self.path}: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "处理模板文件失败")

    def return_favicon(self):
        """返回favicon.ico"""
        # 从配置或默认值获取favicon路径
        favicon_file_path = config.get('FAVICON_FILE', 'templates/favicon.ico') 
        # 构建绝对路径
        favicon_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), favicon_file_path)

        if os.path.exists(favicon_full_path):
            try:
                with open(favicon_full_path, 'rb') as f:
                    content = f.read()
                self.send_response(HTTPStatus.OK)
                # 根据文件扩展名确定 Content-Type
                content_type = 'image/x-icon' # 默认
                if favicon_full_path.lower().endswith('.png'):
                    content_type = 'image/png'
                elif favicon_full_path.lower().endswith('.svg'):
                    content_type = 'image/svg+xml'
                elif favicon_full_path.lower().endswith('.jpg') or favicon_full_path.lower().endswith('.jpeg'):
                    content_type = 'image/jpeg'
                # 可以根据需要添加更多类型
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                logger.debug(f"Served favicon from {favicon_full_path}")
            except IOError as e:
                logger.error(f"IOError serving favicon {favicon_full_path}: {e}")
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error reading favicon")
            except Exception as e:
                logger.error(f"Unexpected error serving favicon {favicon_full_path}: {e}")
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error serving favicon")
        else:
            logger.warning(f"Favicon file not found at {favicon_full_path}. Sending 404.")
            # 发送一个明确的 404 Not Found 响应
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Favicon not found')

    def return_html(self, body, status_code=HTTPStatus.OK):
        encoded = body.encode(config.get("TEMPLATE_ENCODING", "utf-8"))
        self.send_response(status_code)
        self.send_header('Content-Length', len(encoded))
        self.send_header('Content-Type', 'text/html; charset={}'.format(config.get("TEMPLATE_ENCODING", "utf-8")))
        self.end_headers()
        self.wfile.write(encoded)

    def pre_process_path(self):
        # 支持通过 URL 参数进行跳转
        if self.path.startswith('/?url='):
            self.path = self.path.replace('/?url=', '/', 1)
        # 如果路径以域名开头，则自动补全协议
        if self.is_start_with_domain(self.path[1:]):
            self.path = '/https://' + self.path[1:]
        # 如果非代理请求，则尝试从 Referer 中补全路径
        if not (self.path[1:].startswith('http://') or self.path[1:].startswith('https://')):
            referer = self.get_request_header('Referer')
            if referer is not None and parse.urlparse(referer.replace(config['SERVER'], '')).netloc != '':
                self.path = '/' + referer.replace(config['SERVER'], '') + self.path

    def get_request_cookie(self, cookie_name):
        cookies = ""
        for header in self.headers._headers:
            if header[0].lower() == 'cookie':
                cookies = header[1].split('; ')
                break
        
        # 过滤无效的 Cookie
        valid_cookies = []
        for cookie in cookies:
            parts = cookie.split('=')
            if len(parts) == 2 and parts[0] and parts[1]:  # 确保 Cookie 名和值都不为空
                valid_cookies.append(cookie)
        
        # 从有效的 Cookie 中查找目标 Cookie
        for cookie in valid_cookies:
            parts = cookie.split('=')
            if parts[0] == cookie_name:
                return parts[1]
        return ""

    def get_request_header(self, header_name):
        for header in self.headers._headers:
            if header[0].lower() == header_name.lower():
                return header[1]
        return None

    def version_string(self):
        return self.server_name

    def redirect_to_login(self):
        self.send_response(HTTPStatus.FOUND)
        self.send_header('Location', self.login_path)
        self.end_headers()

    def is_start_with_domain(self, string):
        domain = self.domain_re.match(string)
        psl = PublicSuffixList()
        if domain is None or domain.group(1)[1:] not in psl.tlds:
            return False
        return True

# ------------------ 多线程 HTTP 服务器 ------------------
class ThreadingHttpServer(ThreadingMixIn, http.server.HTTPServer):
    # 设置线程池大小，防止线程爆炸
    daemon_threads = True  # 使用守护线程
    # 限制最大线程数
    max_worker_threads = 200  # 根据服务器性能调整
    
    def __init__(self, *args, **kwargs):
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_worker_threads,
            thread_name_prefix="SilkRoad-Worker"
        )
        super().__init__(*args, **kwargs)
    
    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)
    
    def process_request(self, request, client_address):
        # 使用线程池处理请求，而不是为每个请求创建新线程
        self._thread_pool.submit(self.process_request_thread, request, client_address)

# ------------------ 主程序入口 ------------------
if __name__ == '__main__':
    # 设置日志 - 在高并发模式下调整日志级别
    if config.get("PERFORMANCE", {}).get("ENABLE_PERFORMANCE_MODE", True):
        logger.add(config['LOG_FILE'], rotation="500 MB", level="WARNING")  # 只记录警告和错误
    else:
        logger.add(config['LOG_FILE'], rotation="500 MB", level="INFO")
    
    # 初始化HTTP客户端连接池
    http_client_pool = HttpClientPool(pool_size=config.get("PERFORMANCE", {}).get("HTTP_CLIENT_POOL_SIZE", 100))
    
    # 设置线程池大小
    ThreadingHttpServer.max_worker_threads = config.get("PERFORMANCE", {}).get("MAX_WORKER_THREADS", 200)
    
    # 执行系统自检和缓存清理
    system_check_and_cleanup()
    
    # 添加客户端缓存和cookie清理的响应头处理
    class ClientCacheCleaner:
        """用于清除客户端缓存和Cookie的工具类"""
        @staticmethod
        def add_cache_clearing_headers(handler):
            """添加清除缓存的HTTP头"""
            handler.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            handler.send_header('Pragma', 'no-cache')
            handler.send_header('Expires', '0')
    
    # 扩展请求处理器，添加清除客户端缓存的功能
    original_end_headers = SilkRoadHTTPRequestHandler.end_headers
    
    def custom_end_headers(self):
        """扩展end_headers方法，添加清除缓存的头"""
        if hasattr(self, 'clear_client_cache') and self.clear_client_cache:
            ClientCacheCleaner.add_cache_clearing_headers(self)
        original_end_headers(self)
    
    # 替换原始方法
    SilkRoadHTTPRequestHandler.end_headers = custom_end_headers
    
    # 在首次请求时清除客户端缓存
    original_do_request = SilkRoadHTTPRequestHandler.do_request
    
    def custom_do_request(self):
        """扩展do_request方法，在首次请求时清除客户端缓存"""
        # 标记是否需要清除客户端缓存
        self.clear_client_cache = True
        original_do_request(self)
    
    # 替换原始方法
    SilkRoadHTTPRequestHandler.do_request = custom_do_request
    
    # 启动HTTP服务器
    server_address = (config['BIND_IP'], config['PORT'])
    with ThreadingHttpServer(server_address, SilkRoadHTTPRequestHandler) as httpd:
        if config['SCHEME'] == 'https':
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=config['CERT_FILE'], keyfile=config['KEY_FILE'])
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        logger.info('系统启动完成！服务运行在 {} 端口 {} ({}://{}:{}...)',
                    config["BIND_IP"], config["PORT"], config["SCHEME"], config["DOMAIN"], config["PORT"])
        try:
            httpd.serve_forever()
        except Exception as e:
            logger.error("服务器错误: {}", e)