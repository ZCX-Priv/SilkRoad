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
                background-color: rgba(40, 44, 52, 0.85); /* 夜间模式背景色 */
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
            /* 白昼模式的dock栏样式 */
            .silkroad-dock.light-mode {
                background-color: rgba(240, 240, 240, 0.85);
                color: #333;
                box-shadow: 0 5px 25px rgba(0, 0, 0, 0.15);
            }
            /* 白昼模式下的按钮和图标颜色 */
            .silkroad-dock.light-mode .silkroad-dock-button svg,
            .silkroad-dock.light-mode .silkroad-dock-clear svg,
            .silkroad-dock.light-mode .silkroad-dock-theme svg,
            .silkroad-dock.light-mode .silkroad-dock-handle svg {
                fill: #333;
            }
            .silkroad-dock-theme {
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
                margin-left: 15px; /* 右边距，与扫把按钮间隔 */
            }
            .silkroad-dock-theme:hover {
                background-color: rgba(255, 255, 255, 0.15);
                transform: translateY(-3px);
            }
            .silkroad-dock-theme svg {
                width: 20px;
                height: 20px;
                fill: white;
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
            .silkroad-dock.collapsed .silkroad-dock-clear,
            .silkroad-dock.collapsed .silkroad-dock-theme {
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
                position: fixed; /* 改为fixed以便固定在屏幕中央 */
                top: 50%; /* 从顶部50%开始 */
                left: 50%;
                transform: translate(-50%, -50%); /* 水平和垂直方向都居中 */
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
                /* 移除bottom属性，因为我们现在使用top和transform来居中 */
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
        
        // 检查并应用保存的主题设置
        try {
            const savedTheme = localStorage.getItem('silkroad-theme') || 'dark'; // 默认夜间模式
            if (savedTheme === 'light') {
                document.body.classList.add('light-mode');
            } else {
                document.body.classList.add('dark-mode'); // 默认夜间模式
            }
        } catch (e) {
            console.error('读取主题设置失败:', e);
            document.body.classList.add('dark-mode'); // 出错时默认使用夜间模式
        }
        
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
            // 直接跳转到根路径
            window.location.href = '/';
        });
        buttons.appendChild(homeBtn);
        
        // 返回上一页按钮
        const backBtn = document.createElement('button');
        backBtn.className = 'silkroad-dock-button';
        backBtn.title = '返回上一页';
        backBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"/></svg>`;
        backBtn.addEventListener('click', function() {
            window.history.back();
        });
        buttons.appendChild(backBtn);
        
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
        
        // 提取并显示实际访问的URL（去除代理前缀）- 增强健壮性
        let currentUrl = '';
        try {
            currentUrl = window.location.href || '';
            
            // 尝试从代理URL中提取实际URL
            if (currentUrl) {
                const proxyMatch = currentUrl.match(/https?:\/\/[^\/]+\/(https?:\/\/.+)/);
                if (proxyMatch && proxyMatch[1] && proxyMatch[1].startsWith('http')) {
                    currentUrl = proxyMatch[1];
                }
            }
        } catch (e) {
            console.error('获取URL失败:', e);
            currentUrl = '无法获取URL';
        }
        
        // 确保URL不为空
        if (!currentUrl) {
            currentUrl = '无法获取URL';
        }
        
        urlDisplay.textContent = currentUrl;
        dock.appendChild(urlDisplay);
        
        // 白昼/夜间模式切换按钮 - 放在URL容器右侧，扫把按钮左侧
        const themeToggleBtn = document.createElement('button');
        themeToggleBtn.className = 'silkroad-dock-theme';
        themeToggleBtn.title = '切换白昼/夜间模式';
        // 默认显示月亮图标（表示当前是夜间模式，点击后切换到白昼模式）
        themeToggleBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z"></path></svg>`;
        
        // 设置默认为夜间模式（不添加类，因为默认就是夜间模式）
        
        // 添加点击事件
        themeToggleBtn.addEventListener('click', function() {
            // 切换dock栏的类名
            if (dock.classList.contains('light-mode')) {
                // 切换到夜间模式
                dock.classList.remove('light-mode');
                // 更改图标为月亮（表示当前是夜间模式，点击后切换到白昼模式）
                themeToggleBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.8C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95M17.33,17.97C14.5,17.81 11.7,16.64 9.53,14.5C7.36,12.31 6.2,9.5 6.04,6.68C3.23,9.82 3.34,14.64 6.35,17.66C9.37,20.67 14.19,20.78 17.33,17.97Z"></path></svg>`;
                
                // 显示通知
                const themeNotification = notification.cloneNode(true);
                themeNotification.innerHTML = `<span>已切换到夜间模式</span>`;
                document.body.appendChild(themeNotification);
                setTimeout(function() {
                    themeNotification.classList.add('show');
                    setTimeout(function() {
                        themeNotification.classList.remove('show');
                        setTimeout(function() {
                            if (themeNotification.parentNode) {
                                themeNotification.parentNode.removeChild(themeNotification);
                            }
                        }, 300);
                    }, 2000);
                }, 10);
            } else {
                // 切换到白昼模式
                dock.classList.add('light-mode');
                // 更改图标为太阳（表示当前是白昼模式，点击后切换到夜间模式）
                themeToggleBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,2L14.39,5.42C13.65,5.15 12.84,5 12,5C11.16,5 10.35,5.15 9.61,5.42L12,2M3.34,7L7.5,6.65C6.9,7.16 6.36,7.78 5.94,8.5C5.5,9.24 5.25,10 5.11,10.79L3.34,7M3.36,17L5.12,13.23C5.26,14 5.53,14.78 5.95,15.5C6.37,16.24 6.91,16.86 7.5,17.37L3.36,17M20.65,7L18.88,10.79C18.74,10 18.47,9.23 18.05,8.5C17.63,7.78 17.1,7.15 16.5,6.64L20.65,7M20.64,17L16.5,17.36C17.09,16.85 17.62,16.22 18.04,15.5C18.46,14.77 18.73,14 18.87,13.21L20.64,17M12,22L9.59,18.56C10.33,18.83 11.14,19 12,19C12.82,19 13.63,18.83 14.37,18.56L12,22Z"></path></svg>`;
                
                // 显示通知
                const themeNotification = notification.cloneNode(true);
                themeNotification.innerHTML = `<span>已切换到白昼模式</span>`;
                document.body.appendChild(themeNotification);
                setTimeout(function() {
                    themeNotification.classList.add('show');
                    setTimeout(function() {
                        themeNotification.classList.remove('show');
                        setTimeout(function() {
                            if (themeNotification.parentNode) {
                                themeNotification.parentNode.removeChild(themeNotification);
                            }
                        }, 300);
                    }, 2000);
                }, 10);
            }
            
            // 保存用户偏好到localStorage
            try {
                localStorage.setItem('silkroad-dock-theme', dock.classList.contains('light-mode') ? 'light' : 'dark');
            } catch (e) {
                console.error('保存主题偏好失败:', e);
            }
        });
        
        dock.appendChild(themeToggleBtn);

        // 清除缓存按钮（扫把）- 放在URL容器右侧
        const clearCacheBtn = document.createElement('button'); // 修正拼写错误：buttom -> button
        clearCacheBtn.className = 'silkroad-dock-clear'; 
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
            // 确保有URL可复制
            if (!currentUrl || currentUrl === '无法获取URL') {
                // 创建通知元素的副本
                const errorNotification = notification.cloneNode(true);
                errorNotification.innerHTML = `<span>无法获取有效URL</span>`;
                
                // 显示通知
                document.body.appendChild(errorNotification);
                setTimeout(function() {
                    errorNotification.classList.add('show');
                    
                    // 2秒后隐藏通知
                    setTimeout(function() {
                        errorNotification.classList.remove('show');
                        
                        // 动画完成后移除通知元素
                        setTimeout(function() {
                            if (errorNotification.parentNode) {
                                errorNotification.parentNode.removeChild(errorNotification);
                            }
                        }, 300);
                    }, 2000);
                }, 10);
                return;
            }
            
            // 创建临时文本区域
            const textarea = document.createElement('textarea');
            textarea.value = currentUrl;
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            
            try {
                // 选择文本并复制
                textarea.select();
                const successful = document.execCommand('copy');
                
                // 移除临时元素
                document.body.removeChild(textarea);
                
                // 显示通知
                const copyNotification = notification.cloneNode(true);
                copyNotification.innerHTML = `<span>${successful ? '链接已复制到剪贴板' : '复制失败，请重试'}</span>`;
                
                document.body.appendChild(copyNotification);
                setTimeout(function() {
                    copyNotification.classList.add('show');
                    
                    // 2秒后隐藏通知
                    setTimeout(function() {
                        copyNotification.classList.remove('show');
                        
                        // 动画完成后移除通知元素
                        setTimeout(function() {
                            if (copyNotification.parentNode) {
                                copyNotification.parentNode.removeChild(copyNotification);
                            }
                        }, 300);
                    }, 2000);
                }, 10);
            } catch (e) {
                console.error('复制URL失败:', e);
                // 移除临时元素
                if (textarea.parentNode) {
                    document.body.removeChild(textarea);
                }
                
                // 显示错误通知
                const errorNotification = notification.cloneNode(true);
                errorNotification.innerHTML = `<span>复制失败，请重试</span>`;
                
                document.body.appendChild(errorNotification);
                setTimeout(function() {
                    errorNotification.classList.add('show');
                    
                    // 2秒后隐藏通知
                    setTimeout(function() {
                        errorNotification.classList.remove('show');
                        
                        // 动画完成后移除通知元素
                        setTimeout(function() {
                            if (errorNotification.parentNode) {
                                errorNotification.parentNode.removeChild(errorNotification);
                            }
                        }, 300);
                    }, 2000);
                }, 10);
            }
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
