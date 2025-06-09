# SilkRoad-Proxy

SilkRoad-Proxy是一个功能强大的HTTP/HTTPS代理服务器，提供网页访问、用户认证、缓存管理、链接修正和自定义脚本注入等功能。它采用Python编写，基于httpx库实现高效的HTTP请求处理。

## 功能特点

- **HTTP/HTTPS代理**：支持HTTP和HTTPS协议的代理请求
- **用户认证系统**：提供基于用户名和密码的认证机制
- **会话管理**：使用Cookie实现会话持久化
- **缓存系统**：智能缓存HTML、媒体和其他响应内容
- **链接自动修正**：自动修正HTML中的链接，确保通过代理正常访问
- **自定义脚本注入**：支持向页面注入自定义JavaScript脚本
- **资源管理**：定时垃圾回收和缓存清理
- **黑名单过滤**：支持网站黑名单配置
- **自定义错误页面**：美观的错误提示页面

## 系统要求

- Python 3.6+
- 依赖库：httpx==0.28.1, loguru==0.7.3, publicsuffix2==2.20191221

## 安装指南

1. 克隆仓库到本地

```bash
git clone https://github.com/yourusername/SilkRoad-Proxy.git
cd SilkRoad-Proxy
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

配置文件位于 `databases/config.json`，可以根据需要修改以下参数：

- `CERT_FILE`/`KEY_FILE`: SSL证书和密钥文件路径
- `FAVICON_FILE`: 网站图标文件路径
- `INDEX_FILE`/`LOGIN_FILE`: 主页和登录页模板文件路径
- `CHAT_FILE`: 聊天页面模板文件路径
- `FORBIDDEN_FILE`/`NOT_FOUND_FILE`: 403禁止访问和404页面未找到模板文件路径
- `LOG_FILE`: 日志文件路径
- `LOGIN_PATH`: 登录页面路径
- `FAVICON_PATH`: 网站图标路径
- `CACHE_ENABLED`: 是否启用缓存
- `CACHE_HTML`/`CACHE_MEDIA`/`CACHE_OTHER`: HTML、媒体和其他文件的缓存设置
- `CACHE_LARGE_FILES`: 是否缓存大文件
- `SERVER_NAME`: 服务器名称
- `SESSION_COOKIE_NAME`: 会话Cookie名称
- `SCHEME`: 协议（http/https）
- `DOMAIN`: 域名
- `BIND_IP`: 绑定IP地址
- `PORT`: 端口号
- `SERVER`: 服务器URL

## 用户管理

用户信息存储在 `databases/users.json` 文件中，格式为：

```json
{
    "username1": "password1",
    "username2": "password2"
}
```

## 黑名单管理

网站黑名单配置在 `databases/blacklist.json` 文件中。

## 使用方法

1. 启动代理服务器

```bash
python SilkRoad.py
```

2. 在浏览器中访问配置的地址和端口（默认为 http://127.0.0.1:8080）

3. 使用配置的用户名和密码登录

4. 通过代理访问网站，格式为：`http://127.0.0.1:8080/http://example.com`

## 使用Nginx反向代理

如果您希望在生产环境中使用SilkRoad-Proxy，可以配置Nginx作为反向代理，提供更好的性能和安全性。

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向HTTP到HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    # SSL证书配置
    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # 反向代理到SilkRoad-Proxy
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 配置说明

1. 将 `your-domain.com` 替换为您的实际域名
2. 更新SSL证书路径为您的实际证书路径
3. 确保SilkRoad-Proxy在本地运行（默认为127.0.0.1:8080）
4. 如果您修改了SilkRoad-Proxy的端口，请相应地更新`proxy_pass`配置

### 优势

- **SSL终止**：Nginx处理SSL连接，减轻SilkRoad-Proxy的负担
- **负载均衡**：可以配置多个SilkRoad-Proxy实例实现负载均衡
- **安全性增强**：Nginx可以配置额外的安全措施，如限制请求率、IP过滤等
- **静态资源缓存**：Nginx可以缓存静态资源，减少SilkRoad-Proxy的负载

## 开机自启

- 使用 `添加开机自启.bat` 将程序添加到Windows开机启动项
- 使用 `解除开机自启.bat` 移除开机启动项

## 安全说明

- 默认SSL证书仅用于开发测试，生产环境请替换为有效的SSL证书
- 请妥善保管用户凭据信息
- 建议在生产环境中修改默认端口和凭据

## 技术实现

### 核心组件

- **HttpClientPool**：HTTP客户端连接池，管理和复用httpx客户端实例
- **CacheManager**：缓存管理系统，负责缓存响应内容和定期清理过期缓存
- **ScriptManager**：脚本管理器，加载和注入自定义JavaScript脚本
- **SilkRoadHTTPRequestHandler**：HTTP请求处理器，处理代理请求和响应

### 性能优化

- 定时垃圾回收，减少内存占用
- 连接池复用HTTP客户端，减少连接建立开销
- 智能缓存系统，减少重复请求
- 退出时自动清理临时文件和缓存

### 自定义脚本功能

SilkRoad-Proxy支持向代理页面注入自定义JavaScript脚本，提供以下功能：

- **dock.js**：底部浮动Dock栏，提供返回首页、刷新页面、清除缓存等功能
- **progress.js**：页面加载进度条，提供视觉反馈
- **target.js**：链接转换器，将新标签页链接改为在同一页面打开

## 项目结构

```
SilkRoad-Proxy/
├── LICENSE
├── Readme.md
├── SilkRoad.py          # 主程序
├── SilkRoad.log         # 日志文件
├── databases/           # 数据文件目录
│   ├── blacklist.json   # 黑名单配置
│   ├── config.json      # 系统配置
│   └── users.json       # 用户数据
├── scripts/             # 自定义脚本目录
│   ├── dock.js          # 底部Dock栏脚本
│   ├── progress.js      # 页面加载进度条脚本
│   └── target.js        # 链接转换器脚本
├── ssl/                 # SSL证书目录
│   ├── cert.pem         # 证书文件
│   └── key.pem          # 密钥文件
├── static/              # 静态资源目录
│   ├── css/             # CSS样式文件
│   │   ├── all.min.css
│   │   ├── animation.css
│   │   ├── error.css
│   │   ├── font.css
│   │   ├── github.min.css
│   │   ├── iconfont.css
│   │   ├── iziToast.min.css
│   │   ├── katex.min.css
│   │   ├── loading.css
│   │   ├── mobile.css
│   │   └── style.css
│   ├── font/            # 字体文件
│   │   ├── MiSans-Regular.subset.ttf
│   │   ├── MiSans-Regular.subset.woff2
│   │   ├── MiSans-Regular.woff2
│   │   ├── iconfont-exp.eot
│   │   ├── iconfont-exp.svg
│   │   ├── iconfont-exp.ttf
│   │   ├── iconfont-exp.woff
│   │   ├── iconfont-exp.woff2
│   │   ├── iconfont.ttf
│   │   ├── iconfont.woff
│   │   └── iconfont.woff2
│   ├── img/             # 图片资源
│   │   ├── background1.webp
│   │   ├── background10.webp
│   │   ├── background2.webp
│   │   ├── background3.webp
│   │   ├── background4.webp
│   │   ├── background5.webp
│   │   ├── background6.webp
│   │   ├── background7.webp
│   │   ├── background8.webp
│   │   ├── background9.webp
│   │   └── silkroad.jpg
│   └── js/              # JavaScript文件
│       ├── auto-render.min.js
│       ├── bash.min.js
│       ├── core.min.js
│       ├── cpp.min.js
│       ├── iziToast.min.js
│       ├── java.min.js
│       ├── javascript.min.js
│       ├── jquery.min.js
│       ├── js.cookie.js
│       ├── katex.min.js
│       ├── main.js
│       ├── marked.min.js
│       ├── python.min.js
│       └── set.js
├── temp/                # 临时文件目录
│   ├── html/
│   ├── media/
│   └── responses/
├── templates/           # 页面模板目录
│   ├── 403.html         # 禁止访问页面
│   ├── 404.html         # 页面未找到
│   ├── chat.html        # 聊天页面
│   ├── index.html       # 主页
│   └── login.html       # 登录页
├── favicon.ico          # 网站图标
├── requirements.txt     # 依赖库列表
├── 丝绸之路（未来规划）.txt # 未来规划文档
├── 添加开机自启.bat      # 添加开机自启脚本
└── 解除开机自启.bat      # 解除开机自启脚本
```

## 使用示例

### 基本代理访问

```
http://127.0.0.1:8080/http://example.com
```

### 使用URL参数

```
http://127.0.0.1:8080/?url=http://example.com
```

### 清除缓存

使用Dock栏中的清除缓存按钮，或手动删除temp目录下的缓存文件。

## 未来规划

以下功能正在计划中：

- 移植zmirror链接替换规则、线程管理、缓存系统和连接池
- 支持流式响应请求
- 完善黑名单功能，访问黑名单中的网址时返回403.html
- 支持Cloudflare的5秒盾以及其他网站环境安全检查
- 密码错误五次后自动禁止登录五分钟
- 支持修改CSS和JS中的链接
- 优化网页界面，使用"安卓开关"替代"/"控制搜索引擎代理开关
- 完善安卓开关状态显示（开绿关红/文字）

## 常见问题

### Q: 如何添加新用户？
A: 编辑 `databases/users.json` 文件，添加新的用户名和密码。

### Q: 如何修改端口号？
A: 在 `databases/config.json` 中修改 `PORT` 参数。

### Q: 如何禁用缓存？
A: 在 `databases/config.json` 中将 `CACHE_ENABLED` 设置为 `false`。

### Q: 如何添加自定义脚本？
A: 在 `scripts` 目录下创建新的 `.js` 文件，系统会自动加载并注入到代理页面中。

## 许可证

请查看项目中的 LICENSE 文件了解许可证信息。

## 贡献指南

欢迎提交问题报告和功能建议，也欢迎通过Pull Request贡献代码。