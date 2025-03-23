import ssl
import re
import random
import string
import time
import json
import http.server
import http.client
from http import HTTPStatus
from socketserver import ThreadingMixIn
from urllib import parse
from threading import Timer, Thread
import hashlib
import base64
import os
import shutil
import gc
import atexit
import signal
import sys
import platform
from loguru import logger

# Windows 平台下用于管理员权限检测
if platform.system() == "Windows":
    import ctypes

# ------------------ 配置与数据加载 ------------------
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_json('databases/config.json')
users_data = load_json('databases/users.json')
blacklist_domains = load_json('databases/blacklist.json')

# 加载自定义页面
with open(config['ERROR_FILE'], 'r', encoding='utf-8') as ef:
    error_page = ef.read()
with open(config['BLOCK_FILE'], 'r', encoding='utf-8') as bf:
    block_page = bf.read()

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
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        logger.info("Cleared temp cache directory.")

atexit.register(clear_temp_cache)

def check_admin_privileges():
    """检查是否以管理员权限运行"""
    if platform.system() == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            logger.error("Admin check failed: {}", e)
            is_admin = False
    else:
        is_admin = os.geteuid() == 0
    if not is_admin:
        logger.warning("程序未以管理员权限运行，部分功能可能受限。")
    else:
        logger.info("管理员权限检测通过。")
    return is_admin

check_admin_privileges()

def exit_confirmation():
    """退出程序时弹出确认对话框"""
    print("\n检测到退出信号。是否退出程序？(y/N): ", end='', flush=True)
    response = sys.stdin.readline().strip().lower()
    return response == 'y'

def signal_handler(sig, frame):
    if exit_confirmation():
        logger.info("程序退出，正在清理缓存...")
        sys.exit(0)
    else:
        logger.info("继续运行程序。")

signal.signal(signal.SIGINT, signal_handler)

# ------------------ 会话与用户管理 ------------------
class Sessions:
    def __init__(self, length=64, age=604800, recycle_interval=3600):
        self.charset = string.ascii_letters + string.digits
        self.length = length
        self.age = age
        self.recycle_interval = recycle_interval
        self.sessions = []
        self.recycle_session()

    def generate_new_session(self):
        new_session = ''.join(random.choice(self.charset) for _ in range(self.length))
        self.sessions.append([new_session, time.time()])
        return new_session

    def is_session_exist(self, session):
        for s in self.sessions:
            if s[0] == session:
                s[1] = time.time()
                return True
        return False

    def recycle_session(self):
        now = time.time()
        self.sessions = [s for s in self.sessions if now - s[1] <= self.age]
        Timer(self.recycle_interval, self.recycle_session).start()

sessions = Sessions()

class Users:
    def __init__(self):
        self.users = users_data

    def is_effective_user(self, user_name, password):
        return user_name in self.users and password == self.users.get(user_name)

users = Users()

# ------------------ 模板管理 ------------------
class Template:
    def __init__(self):
        encoding = config.get("TEMPLATE_ENCODING", "utf-8")
        with open(config['INDEX_FILE'], encoding=encoding) as f:
            self.index_html = f.read()
        with open(config['LOGIN_FILE'], encoding=encoding) as f:
            self.login_html = f.read()

    def get_index_html(self):
        return self.index_html

    def get_login_html(self, login_failed=False):
        return self.login_html.format(login_failed=1 if login_failed else 0)

template = Template()

# ------------------ 浏览器信息伪装 ------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

# ------------------ 缓存操作 ------------------
class Cache:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def get_cache_path(self, key):
        return os.path.join(self.base_dir, hashlib.md5(key.encode('utf-8')).hexdigest())

    def read(self, key):
        path = self.get_cache_path(key)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                logger.info("使用缓存文件: {}", path)
                return f.read()
        return None

    def write(self, key, content):
        path = self.get_cache_path(key)
        try:
            with open(path, 'wb') as f:
                f.write(content)
            logger.info("已缓存文件: {}", path)
        except Exception as e:
            logger.error("缓存写入失败: {}", e)

cache = Cache(os.path.join(os.path.dirname(__file__), "temp", "cache"))

# ------------------ 代理处理 ------------------
class Proxy:
    def __init__(self, handler):
        self.handler = handler
        self.url = self.handler.path[1:]
        parse_result = parse.urlparse(self.url)
        self.scheme = parse_result.scheme
        self.netloc = parse_result.netloc
        self.site = self.scheme + '://' + self.netloc
        self.path = parse_result.path

        # 黑名单检测
        if self.netloc in blacklist_domains:
            self.send_block_page()
            raise Exception("目标域名在黑名单中: " + self.netloc)

    def proxy(self):
        # 判断是否为 WebSocket 请求
        if self.handler.headers.get('Upgrade', '').lower() == 'websocket':
            self.process_websocket()
            return

        self.process_request()
        content_length = int(self.handler.headers.get('Content-Length', 0))
        data = self.handler.rfile.read(content_length) if content_length > 0 else None

        # 仅对 GET 请求启用缓存
        if self.handler.command.upper() == 'GET':
            cached = cache.read(self.url)
            if cached is not None:
                self.process_response(None, cached, cached=True)
                return

        try:
            import httpx
            headers = {k: v for k, v in self.handler.headers.items()}
            headers['User-Agent'] = random.choice(USER_AGENTS)
            with httpx.Client(verify=False, follow_redirects=False, timeout=30.0) as client:
                r = client.request(method=self.handler.command, url=self.url, headers=headers, content=data)
        except Exception as error:
            self.process_error(error)
        else:
            content_type = r.headers.get('Content-Type', '')
            content_to_cache = r.content if (self.handler.command.upper() == 'GET' and 
                                             any(ext in content_type for ext in ["text/html", "text/css", "application/javascript", "image/"])) else None
            self.process_response(r, content_to_cache=content_to_cache)
            if content_to_cache:
                cache.write(self.url, r.content)

    def process_websocket(self):
        # 完整实现 WebSocket 双向代理
        client_key = self.handler.headers.get('Sec-WebSocket-Key')
        if not client_key:
            self.handler.send_error(HTTPStatus.BAD_REQUEST, "缺少 Sec-WebSocket-Key")
            return

        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_val = base64.b64encode(hashlib.sha1((client_key + GUID).encode('utf-8')).digest()).decode('utf-8')
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: {}\r\n\r\n"
        ).format(accept_val)
        self.handler.connection.send(response.encode())

        # 建立远端 WebSocket 连接
        import socket
        target_host = self.netloc
        target_port = 443 if self.scheme in ("wss", "https") else 80
        try:
            remote_sock = socket.create_connection((target_host, target_port), timeout=10)
        except Exception as e:
            logger.error("连接远程 WebSocket 服务器失败: {}", e)
            return
        if self.scheme in ("wss", "https"):
            context = ssl.create_default_context()
            remote_sock = context.wrap_socket(remote_sock, server_hostname=target_host)

        remote_key = base64.b64encode(os.urandom(16)).decode('utf-8')
        handshake_req = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).format(self.path, target_host, remote_key)
        remote_sock.send(handshake_req.encode())
        try:
            remote_resp = remote_sock.recv(4096)
            logger.info("远程 WebSocket 握手响应: {}", remote_resp.decode('utf-8', errors='replace'))
        except Exception as e:
            logger.error("读取远程 WebSocket 握手响应失败: {}", e)
            return

        def forward(source, dest):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break
                    dest.sendall(data)
            except Exception as e:
                logger.error("WebSocket 转发错误: {}", e)
            finally:
                for sock in (source, dest):
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                        sock.close()
                    except Exception:
                        pass

        t1 = Thread(target=forward, args=(self.handler.connection, remote_sock))
        t2 = Thread(target=forward, args=(remote_sock, self.handler.connection))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def process_request(self):
        client_conn = self.handler.headers.get('Connection', '').lower()
        conn_value = 'keep-alive' if client_conn == 'keep-alive' else 'close'
        self.modify_request_header('Referer', lambda x: x.replace(config['SERVER'], ''))
        self.modify_request_header('Origin', self.site)
        self.modify_request_header('Host', self.netloc)
        if 'Accept-Language' not in self.handler.headers:
            self.handler.headers.add_header('Accept-Language', 'en-US,en;q=0.9')
        self.modify_request_header('Accept-Encoding', 'identity')
        self.modify_request_header('Connection', conn_value)

    def process_response(self, r, content_to_cache=None, cached=False):
        if not cached:
            content_type = r.headers.get('Content-Type', '')
            if "text/html" in content_type:
                content = self.revision_link(r.content, r.encoding)
            else:
                content = r.content if r.content is not None else b''
        else:
            content = content_to_cache
        content_length = len(content)
        if not cached:
            self.handler.send_response(r.status_code)
            if "Content-Range" in r.headers:
                self.handler.send_header("Content-Range", r.headers["Content-Range"])
            if "location" in r.headers:
                self.handler.send_header('Location', self.revision_location(r.headers['location']))
            if "content-type" in r.headers:
                self.handler.send_header('Content-Type', r.headers['content-type'])
            if "set-cookie" in r.headers:
                self.revision_set_cookie(r.headers['set-cookie'])
        else:
            self.handler.send_response(200)
            self.handler.send_header('Content-Type', 'text/html; charset=utf-8')
        self.handler.send_header('Content-Length', content_length)
        client_conn = self.handler.headers.get('Connection', '').lower()
        conn_value = 'keep-alive' if client_conn == 'keep-alive' else 'close'
        self.handler.send_header('Connection', conn_value)
        self.handler.send_header('Access-Control-Allow-Origin', '*')
        self.handler.end_headers()
        if content:
            self.handler.wfile.write(content)

    def process_error(self, error):
        self.handler.send_response(HTTPStatus.BAD_REQUEST)
        self.handler.send_header('Content-Type', 'text/html; charset=utf-8')
        error_content = error_page.replace("{error_info}", str(error))
        encoded = error_content.encode('utf-8')
        self.handler.send_header('Content-Length', len(encoded))
        self.handler.end_headers()
        self.handler.wfile.write(encoded)
        logger.error("Proxy error: {}", error)

    def send_block_page(self):
        self.handler.send_response(HTTPStatus.FORBIDDEN)
        self.handler.send_header('Content-Type', 'text/html; charset=utf-8')
        encoded = block_page.encode('utf-8')
        self.handler.send_header('Content-Length', len(encoded))
        self.handler.end_headers()
        self.handler.wfile.write(encoded)
        logger.warning("Blocked request to blacklisted domain: {}", self.netloc)

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

    def revision_location(self, location):
        if location.startswith('http://') or location.startswith('https://'):
            new_location = config['SERVER'] + location
        elif location.startswith('//'):
            new_location = config['SERVER'] + self.scheme + ':' + location
        elif location.startswith('/'):
            new_location = config['SERVER'] + self.site + location
        else:
            new_location = config['SERVER'] + self.site + self.path + '/' + location
        return new_location

    def revision_link(self, body, coding):
        if coding is None:
            return body
        patterns = [
            (r'((?<=href=[\'"])(http[s]?://))', config['SERVER']),
            (r'((?<=src=[\'"])(http[s]?://))', config['SERVER'])
        ]
        content = body.decode(coding, errors='replace')
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        return content.encode(coding)

    def revision_set_cookie(self, cookies):
        cookie_list = []
        half_cookie = None
        for _cookie in cookies.split(', '):
            if half_cookie:
                cookie_list.append(', '.join([half_cookie, _cookie]))
                half_cookie = None
            elif 'Expires' in _cookie or 'expires' in _cookie:
                half_cookie = _cookie
            else:
                cookie_list.append(_cookie)
        for _cookie in cookie_list:
            self.handler.send_header('Set-Cookie', self.revision_response_cookie(_cookie))

    def revision_response_cookie(self, cookie):
        cookie = re.sub(r'domain\=[^,;]+', 'domain=.{}'.format(config['DOMAIN']), cookie, flags=re.IGNORECASE)
        cookie = re.sub(r'path\=\/', 'path={}/'.format('/' + self.site), cookie, flags=re.IGNORECASE)
        if config['SCHEME'] == 'http':
            cookie = re.sub(r'secure;?', '', cookie, flags=re.IGNORECASE)
        return cookie

# ------------------ HTTP 请求处理 ------------------
class SilkRoadHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # 支持持久连接

    def __init__(self, request, client_address, server):
        self.login_path = config['LOGIN_PATH']
        self.favicon_path = config['FAVICON_PATH']
        self.server_name = config['SERVER_NAME']
        self.session_cookie_name = config['SESSION_COOKIE_NAME']
        self.domain_re = re.compile(r'(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+')
        with open(config['FAVICON_FILE'], 'rb') as f:
            self.favicon_data = f.read()
        super().__init__(request, client_address, server)

    def do_GET(self):
        self.do_request()

    def do_POST(self):
        self.do_request()

    def do_HEAD(self):
        self.do_request()

    def do_request(self):
        self.pre_process_path()
        if self.is_login():
            if self.is_need_proxy():
                try:
                    Proxy(self).proxy()
                except Exception as e:
                    logger.error("Proxy异常: {}", e)
            else:
                self.process_original()
        else:
            self.redirect_to_login()

    def is_login(self):
        if self.path in (self.login_path, self.favicon_path):
            return True
        session = self.get_request_cookie(self.session_cookie_name)
        return sessions.is_session_exist(session)

    def process_original(self):
        if self.path == self.favicon_path:
            self.process_favicon()
        elif self.path == self.login_path:
            self.process_login()
        else:
            self.process_index()

    def process_login(self):
        if self.command == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = parse.parse_qs(parse.unquote(raw_data))
            if 'user' in parsed_data and 'password' in parsed_data:
                if users.is_effective_user(parsed_data['user'][0], parsed_data['password'][0]):
                    session = sessions.generate_new_session()
                    self.send_response(HTTPStatus.FOUND)
                    self.send_header('Location', '/')
                    self.send_header('Set-Cookie',
                                     '{}={}; expires=Sun, 30-Jun-3000 02:06:18 GMT; path=/; HttpOnly'
                                     .format(self.session_cookie_name, session))
                    self.end_headers()
                    return
            body = template.get_login_html(login_failed=True)
        else:
            body = template.get_login_html(login_failed=False)
        self.return_html(body)

    def process_index(self):
        body = template.get_index_html()
        self.return_html(body)

    def process_favicon(self):
        self.send_response(200)
        self.send_header('Content-Type', 'image/x-icon')
        self.end_headers()
        self.wfile.write(self.favicon_data)

    def return_html(self, body):
        encoded = body.encode(config.get("TEMPLATE_ENCODING", "utf-8"))
        self.send_response(200)
        self.send_header('Content-Length', len(encoded))
        self.send_header('Content-Type', 'text/html; charset={}'.format(config.get("TEMPLATE_ENCODING", "utf-8")))
        self.end_headers()
        self.wfile.write(encoded)

    def is_need_proxy(self):
        return self.path[1:].startswith('http://') or self.path[1:].startswith('https://')

    def pre_process_path(self):
        if self.path.startswith('/?url='):
            self.path = self.path.replace('/?url=', '/', 1)
        if self.is_start_with_domain(self.path[1:]):
            self.path = '/https://' + self.path[1:]
        if not self.is_need_proxy():
            referer = self.get_request_header('Referer')
            if referer and parse.urlparse(referer.replace(config['SERVER'], '')).netloc:
                self.path = '/' + referer.replace(config['SERVER'], '') + self.path

    def get_request_cookie(self, cookie_name):
        for header in self.headers._headers:
            if header[0].lower() == 'cookie':
                for cookie in header[1].split('; '):
                    parts = cookie.split('=')
                    if len(parts) == 2 and parts[0] == cookie_name:
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
        from publicsuffix2 import PublicSuffixList
        psl = PublicSuffixList()
        return domain is not None and domain.group(1)[1:] in psl.tlds

# ------------------ 多线程 HTTP 服务器 ------------------
class ThreadingHttpServer(ThreadingMixIn, http.server.HTTPServer):
    pass

# ------------------ 主程序入口 ------------------
if __name__ == '__main__':
    logger.add(config['LOG_FILE'], rotation="500 MB", level="INFO")
    server_address = (config['BIND_IP'], config['PORT'])
    with ThreadingHttpServer(server_address, SilkRoadHTTPRequestHandler) as httpd:
        if config['SCHEME'] == 'https':
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=config['CERT_FILE'], keyfile=config['KEY_FILE'])
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        logger.info('Serving HTTP on {} port {} ({}://{}:{}...)',
                    config["BIND_IP"], config["PORT"], config["SCHEME"], config["DOMAIN"], config["PORT"])
        try:
            httpd.serve_forever()
        except Exception as e:
            logger.error("Server error: {}", e)
