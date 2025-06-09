// SilkRoad自定义脚本 - 底部Dock栏
(function() {
    console.log('底部浮动Dock栏');
    
    // 在页面加载完成后执行
    document.addEventListener('DOMContentLoaded', function() {
        // 创建样式
        const style = document.createElement('style');
        style.textContent = `
            .silkroad-dock {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(40, 44, 52, 0.85);
                color: white;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 9999;
                transition: all 0.3s ease;
                box-shadow: 0 5px 25px rgba(0, 0, 0, 0.25);
                font-family: 'Segoe UI', Arial, sans-serif;
                border-radius: 50px;
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                max-width: 90%;
                width: auto;
            }
            .silkroad-dock.collapsed {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                padding: 0;
                overflow: hidden;
                justify-content: center;
            }
            .silkroad-dock.collapsed .silkroad-dock-buttons,
            .silkroad-dock.collapsed .silkroad-dock-url,
            .silkroad-dock.collapsed .silkroad-dock-clear {
                display: none;
            }
            .silkroad-dock-handle {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background-color: rgba(255, 255, 255, 0.1);
                cursor: pointer;
                display: flex;
                justify-content: center;
                align-items: center;
                transition: all 0.3s ease;
                margin-left: 15px; /* 改为左边距 */
            }
            .silkroad-dock.collapsed .silkroad-dock-handle {
                margin: 0;
                width: 30px;
                height: 30px;
            }
            .silkroad-dock-handle:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            .silkroad-dock-handle svg {
                width: 20px;
                height: 20px;
                fill: white;
                transition: transform 0.3s ease;
                transform: rotate(180deg); /* 默认状态箭头朝下 */
            }
            .silkroad-dock.collapsed .silkroad-dock-handle svg {
                transform: rotate(0deg); /* 折叠状态箭头朝上 */
            }
            .silkroad-dock-buttons {
                display: flex;
                gap: 15px; 
            }
            .silkroad-dock-button {
                background-color: transparent;
                border: none;
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .silkroad-dock-button:hover {
                background-color: rgba(255, 255, 255, 0.15);
                transform: translateY(-3px);
            }
            .silkroad-dock-button svg {
                width: 20px;
                height: 20px;
                fill: white;
            }
            .silkroad-dock-clear {
                background-color: transparent;
                border: none;
                color: white;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                justify-content: center;
                align-items: center;
                margin-left: 15px; /* 改为左边距 */
            }
            .silkroad-dock-clear:hover {
                background-color: rgba(255, 255, 255, 0.15);
                transform: translateY(-3px);
            }
            .silkroad-dock-clear svg {
                width: 20px;
                height: 20px;
                fill: white;
            }
            .silkroad-dock-url {
                flex-grow: 1;
                margin: 0 0 0 20px; /* 只保留左边距 */
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                font-size: 14px;
                opacity: 0.9;
                background-color: rgba(255, 255, 255, 0.1);
                padding: 8px 15px;
                border-radius: 20px;
                max-width: 300px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .silkroad-dock-url:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            .silkroad-notification {
                position: absolute;
                bottom: 80px;  /* 增加初始位置的距离 */
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(40, 44, 52, 0.85);
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-size: 14px;
                box-shadow: 0 5px 25px rgba(0, 0, 0, 0.25);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                z-index: 9998;
                opacity: 0;
                transition: all 0.3s ease;
                pointer-events: none;
                display: flex;
                align-items: center;
            }
            .silkroad-notification.show {
                opacity: 1;
                bottom: 90px;  /* 增加显示时的距离 */
            }
            .silkroad-notification-icon {
                margin-right: 10px;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .silkroad-notification-icon svg {
                width: 20px;
                height: 20px;
                fill: #4CAF50;
            }
        `;
        document.head.appendChild(style);
        
        // 创建dock栏
        const dock = document.createElement('div');
        dock.className = 'silkroad-dock';
        
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = 'silkroad-notification';
        notification.innerHTML = `
            <span>链接已复制到剪贴板</span>
        `;
        
        // 创建按钮区域
        const buttons = document.createElement('div');
        buttons.className = 'silkroad-dock-buttons';

        // 返回首页按钮
        const homeBtn = document.createElement('button');
        homeBtn.className = 'silkroad-dock-button';
        homeBtn.title = '返回首页';
        homeBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z"/></svg>`;
        homeBtn.addEventListener('click', function() {
            // 获取当前URL的域名部分
            const urlObj = new URL(window.location.href);
            const domain = urlObj.origin;
            window.location.href = domain;
        });
        buttons.appendChild(homeBtn);
        
         // 刷新按钮
         const refreshBtn = document.createElement('button');
         refreshBtn.className = 'silkroad-dock-button';
         refreshBtn.title = '刷新页面';
         refreshBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/></svg>`;
         refreshBtn.addEventListener('click', function() {
             location.reload();
         });
         buttons.appendChild(refreshBtn);
        
        dock.appendChild(buttons);
        
        // URL显示区域
        const urlDisplay = document.createElement('div');
        urlDisplay.className = 'silkroad-dock-url';
        urlDisplay.title = '点击复制URL';
        
        // 提取并显示实际访问的URL（去除代理前缀）
        let currentUrl = window.location.href;
        // 尝试从代理URL中提取实际URL
        const proxyMatch = currentUrl.match(/https?:\/\/[^\/]+\/(https?:\/\/.+)/);
        if (proxyMatch && proxyMatch[1]) {
            currentUrl = proxyMatch[1];
        }
        
        urlDisplay.textContent = currentUrl;
        dock.appendChild(urlDisplay);
        
        // 清除缓存按钮（扫把）- 放在URL容器右侧
        const clearCacheBtn = document.createElement('button'); // 修正拼写错误：buttom -> button
        clearCacheBtn.className = 'silkroad-dock-clear'; // 使用handle样式
        clearCacheBtn.title = '清除该网站缓存';
        clearCacheBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M19.36,2.72L20.78,4.14L15.06,9.85C16.13,11.39 16.28,13.24 15.38,14.44L9.06,8.12C10.26,7.22 12.11,7.37 13.65,8.44L19.36,2.72M5.93,17.57C3.92,15.56 2.69,13.16 2.35,10.92L7.23,8.83L14.67,16.27L12.58,21.15C10.34,20.81 7.94,19.58 5.93,17.57Z"/></svg>`;
        
        // 添加点击事件
        clearCacheBtn.addEventListener('click', function() {
            // 清除localStorage
            try {
                localStorage.clear();
            } catch (e) {
                console.error('清除localStorage失败:', e);
            }
            
            // 清除sessionStorage
            try {
                sessionStorage.clear();
            } catch (e) {
                console.error('清除sessionStorage失败:', e);
            }
            
            // 清除所有cookie
            try {
                const cookies = document.cookie.split(";");
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i];
                    const eqPos = cookie.indexOf("=");
                    const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
                    document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
                    // 尝试为域名添加cookie
                    const domain = window.location.hostname;
                    document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=" + domain;
                }
            } catch (e) {
                console.error('清除cookie失败:', e);
            }
            
            // 清除缓存（通过重新加载并跳过缓存）
            // 创建通知元素的副本
            const cacheNotification = notification.cloneNode(true);
            cacheNotification.innerHTML = `<span>已清除该网站缓存</span>`;
            
            // 显示通知
            document.body.appendChild(cacheNotification);
            setTimeout(function() {
                cacheNotification.classList.add('show');
                
                // 2秒后隐藏通知并重新加载页面
                setTimeout(function() {
                    cacheNotification.classList.remove('show');
                    
                    // 动画完成后移除通知元素并刷新页面
                    setTimeout(function() {
                        if (cacheNotification.parentNode) {
                            cacheNotification.parentNode.removeChild(cacheNotification);
                        }
                        // 强制刷新页面（跳过缓存）
                        window.location.reload(true);
                    }, 300);
                }, 2000);
            }, 10);
        });
        
        dock.appendChild(clearCacheBtn);
        
        // 创建折叠把手
        const handle = document.createElement('div');
        handle.className = 'silkroad-dock-handle';
        handle.innerHTML = `<svg viewBox="0 0 24 24"><path d="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z"/></svg>`;
        dock.appendChild(handle);
        
        // 添加点击复制URL功能
        urlDisplay.addEventListener('click', function() {
            // 创建临时文本区域
            const textarea = document.createElement('textarea');
            textarea.value = currentUrl;
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            
            // 选择文本并复制
            textarea.select();
            document.execCommand('copy');
            
            // 移除临时元素
            document.body.removeChild(textarea);
            
            // 显示通知
            document.body.appendChild(notification);
            setTimeout(function() {
                notification.classList.add('show');
                
                // 2秒后隐藏通知
                setTimeout(function() {
                    notification.classList.remove('show');
                    
                    // 动画完成后移除通知元素
                    setTimeout(function() {
                        if (notification.parentNode) {
                            notification.parentNode.removeChild(notification);
                        }
                    }, 300);
                }, 2000);
            }, 10);
        });
        
        // 添加到页面
        document.body.appendChild(dock);
        
        // 折叠/展开功能
        handle.addEventListener('click', function() {
            dock.classList.toggle('collapsed');
            // 保存状态到localStorage
            localStorage.setItem('silkroadDockCollapsed', dock.classList.contains('collapsed'));
        });
        
        // 恢复上次的折叠状态
        if (localStorage.getItem('silkroadDockCollapsed') === 'true') {
            dock.classList.add('collapsed');
        }
    });
})();