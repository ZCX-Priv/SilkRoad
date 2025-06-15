/**
 *URL修正插件
 * 用于拦截后端代理重写时遗漏的链接并自动修正
 * 使用API Hook和DOM Hook技术，不依赖Service Worker
 */

(function() {
    console.log('URL修正插件已加载');
    
    // 配置
    const config = {
        debug: true,                      // 是否启用调试日志
        proxyPrefix: window.location.origin, // 代理服务器前缀
        targetDomain: null,               // 目标网站域名（自动检测）
        ignorePatterns: [                 // 忽略的URL模式
            /^javascript:/,
            /^mailto:/,
            /^tel:/,
            /^#/,
            /^data:/,
            /^blob:/,
            /^about:/
        ],
        alreadyProcessedAttr: 'data-silkroad-fixed' // 标记已处理的元素
    };
    
    // 工具函数
    const utils = {
        log: function(message) {
            if (config.debug) {
                console.log(`[URL修正器] ${message}`);
            }
        },
        
        // 检测URL是否已经被代理
        isProxied: function(url) {
            if (!url || typeof url !== 'string') return true;
            return url.startsWith(config.proxyPrefix + '/');
        },
        
        // 检测URL是否应该被忽略
        shouldIgnore: function(url) {
            if (!url || typeof url !== 'string') return true;
            return config.ignorePatterns.some(pattern => pattern.test(url));
        },
        
        // 修正URL
        fixUrl: function(url) {
            if (!url || typeof url !== 'string') return url;
            if (utils.isProxied(url) || utils.shouldIgnore(url)) return url;
            
            // 处理相对路径
            let absoluteUrl = url;
            if (!url.match(/^https?:\/\//)) {
                const base = config.targetDomain ? 
                    `https://${config.targetDomain}` : 
                    window.location.href.replace(config.proxyPrefix + '/', '');
                
                // 处理绝对路径（以/开头）
                if (url.startsWith('/')) {
                    const baseUrl = new URL(base);
                    absoluteUrl = `${baseUrl.protocol}//${baseUrl.host}${url}`;
                } else {
                    // 处理相对路径
                    absoluteUrl = new URL(url, base).href;
                }
            }
            
            // 添加代理前缀
            return `${config.proxyPrefix}/${absoluteUrl}`;
        },
        
        // 从当前URL中提取目标域名
        extractTargetDomain: function() {
            const currentUrl = window.location.href;
            const match = currentUrl.match(new RegExp(`${config.proxyPrefix}/https?://([^/]+)`));
            return match ? match[1] : null;
        }
    };
    
    // 初始化配置
    function initConfig() {
        // 提取目标域名
        config.targetDomain = utils.extractTargetDomain();
        utils.log(`目标域名: ${config.targetDomain}`);
    }
    
    // ==================== API Hook ====================
    
    // 拦截XMLHttpRequest
    function hookXHR() {
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
            const fixedUrl = utils.fixUrl(url);
            if (fixedUrl !== url) {
                utils.log(`XHR: ${url} -> ${fixedUrl}`);
            }
            return originalOpen.call(this, method, fixedUrl, async, user, password);
        };
        utils.log('已Hook XMLHttpRequest');
    }
    
    // 拦截Fetch API
    function hookFetch() {
        const originalFetch = window.fetch;
        window.fetch = function(input, init) {
            if (typeof input === 'string') {
                const fixedUrl = utils.fixUrl(input);
                if (fixedUrl !== input) {
                    utils.log(`Fetch: ${input} -> ${fixedUrl}`);
                }
                return originalFetch.call(this, fixedUrl, init);
            } else if (input instanceof Request) {
                const fixedUrl = utils.fixUrl(input.url);
                if (fixedUrl !== input.url) {
                    utils.log(`Fetch Request: ${input.url} -> ${fixedUrl}`);
                    input = new Request(fixedUrl, input);
                }
                return originalFetch.call(this, input, init);
            }
            return originalFetch.call(this, input, init);
        };
        utils.log('已Hook Fetch API');
    }
    
    // 拦截WebSocket
    function hookWebSocket() {
        const originalWebSocket = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            // WebSocket URL需要特殊处理，将http/https转为ws/wss
            let fixedUrl = url;
            if (!utils.isProxied(url) && !utils.shouldIgnore(url)) {
                // 将ws://example.com转换为代理的形式
                const wsUrl = url.replace(/^ws/, 'http');
                fixedUrl = utils.fixUrl(wsUrl).replace(/^http/, 'ws');
                utils.log(`WebSocket: ${url} -> ${fixedUrl}`);
            }
            return new originalWebSocket(fixedUrl, protocols);
        };
        window.WebSocket.prototype = originalWebSocket.prototype;
        window.WebSocket.CONNECTING = originalWebSocket.CONNECTING;
        window.WebSocket.OPEN = originalWebSocket.OPEN;
        window.WebSocket.CLOSING = originalWebSocket.CLOSING;
        window.WebSocket.CLOSED = originalWebSocket.CLOSED;
        utils.log('已Hook WebSocket');
    }
    
    // 拦截window.open
    function hookWindowOpen() {
        const originalOpen = window.open;
        window.open = function(url, target, features) {
            const fixedUrl = utils.fixUrl(url);
            if (fixedUrl !== url) {
                utils.log(`window.open: ${url} -> ${fixedUrl}`);
            }
            return originalOpen.call(this, fixedUrl, target, features);
        };
        utils.log('已Hook window.open');
    }
    
    // 拦截document.write/writeln
    function hookDocumentWrite() {
        const originalWrite = document.write;
        const originalWriteln = document.writeln;
        
        document.write = function(markup) {
            // 处理HTML中的URL
            const fixedMarkup = fixHtmlContent(markup);
            return originalWrite.call(this, fixedMarkup);
        };
        
        document.writeln = function(markup) {
            // 处理HTML中的URL
            const fixedMarkup = fixHtmlContent(markup);
            return originalWriteln.call(this, fixedMarkup);
        };
        
        utils.log('已Hook document.write/writeln');
    }
    
    // 修复HTML内容中的URL
    function fixHtmlContent(html) {
        if (!html || typeof html !== 'string') return html;
        
        // 修复常见的URL属性
        let fixed = html.replace(/\b(href|src|action|data-src|formaction|background|poster)\s*=\s*(['"])(.*?)\2/gi, 
            function(match, attr, quote, url) {
                const fixedUrl = utils.fixUrl(url);
                if (fixedUrl !== url) {
                    utils.log(`HTML ${attr}: ${url} -> ${fixedUrl}`);
                    return `${attr}=${quote}${fixedUrl}${quote}`;
                }
                return match;
            });
        
        // 修复CSS中的URL
        fixed = fixed.replace(/url\((['"]?)(.*?)\1\)/gi, 
            function(match, quote, url) {
                const fixedUrl = utils.fixUrl(url);
                if (fixedUrl !== url) {
                    utils.log(`CSS URL: ${url} -> ${fixedUrl}`);
                    return `url(${quote}${fixedUrl}${quote})`;
                }
                return match;
            });
        
        return fixed;
    }
    
    // ==================== DOM Hook ====================
    
    // 处理DOM元素的URL属性
    function processElement(element) {
        // 如果元素已经处理过，跳过
        if (element.hasAttribute(config.alreadyProcessedAttr)) {
            return;
        }
        
        // 标记元素已处理
        element.setAttribute(config.alreadyProcessedAttr, 'true');
        
        // 处理常见的URL属性
        const urlAttributes = ['href', 'src', 'action', 'data-src', 'formaction', 'background', 'poster'];
        
        urlAttributes.forEach(attr => {
            if (element.hasAttribute(attr)) {
                const url = element.getAttribute(attr);
                const fixedUrl = utils.fixUrl(url);
                if (fixedUrl !== url) {
                    utils.log(`DOM ${attr}: ${url} -> ${fixedUrl}`);
                    element.setAttribute(attr, fixedUrl);
                }
            }
        });
        
        // 处理srcset属性（用于响应式图片）
        if (element.hasAttribute('srcset')) {
            const srcset = element.getAttribute('srcset');
            const parts = srcset.split(',');
            const fixedParts = parts.map(part => {
                part = part.trim();
                const [url, descriptor] = part.split(/\s+/, 2);
                const fixedUrl = utils.fixUrl(url);
                if (fixedUrl !== url) {
                    utils.log(`srcset: ${url} -> ${fixedUrl}`);
                    return descriptor ? `${fixedUrl} ${descriptor}` : fixedUrl;
                }
                return part;
            });
            element.setAttribute('srcset', fixedParts.join(', '));
        }
        
        // 处理style属性中的URL
        if (element.hasAttribute('style')) {
            const style = element.getAttribute('style');
            const fixedStyle = style.replace(/url\((['"]?)(.*?)\1\)/gi, 
                function(match, quote, url) {
                    const fixedUrl = utils.fixUrl(url);
                    if (fixedUrl !== url) {
                        utils.log(`Style URL: ${url} -> ${fixedUrl}`);
                        return `url(${quote}${fixedUrl}${quote})`;
                    }
                    return match;
                });
            if (fixedStyle !== style) {
                element.setAttribute('style', fixedStyle);
            }
        }
        
        // 处理内联脚本
        if (element.tagName === 'SCRIPT' && !element.src && element.textContent) {
            // 这里可以添加对内联脚本的处理，但需要更复杂的解析
            // 简单起见，这里不实现
        }
    }
    
    // 处理所有现有元素
    function processAllElements() {
        const elements = document.querySelectorAll('*');
        elements.forEach(processElement);
        utils.log(`已处理 ${elements.length} 个DOM元素`);
    }
    
    // 使用MutationObserver监听DOM变化
    function setupMutationObserver() {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                // 处理新添加的节点
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            processElement(node);
                            
                            // 处理子元素
                            const childElements = node.querySelectorAll('*');
                            childElements.forEach(processElement);
                        }
                    });
                }
                
                // 处理属性变化
                if (mutation.type === 'attributes' && 
                    ['href', 'src', 'action', 'data-src', 'formaction', 'background', 'poster', 'srcset', 'style'].includes(mutation.attributeName)) {
                    processElement(mutation.target);
                }
            });
        });
        
        // 配置观察器
        observer.observe(document.documentElement, {
            childList: true,    // 观察子节点的添加或删除
            subtree: true,      // 观察所有后代节点
            attributes: true,   // 观察属性变化
            attributeFilter: ['href', 'src', 'action', 'data-src', 'formaction', 'background', 'poster', 'srcset', 'style'] // 只关注URL相关属性
        });
        
        utils.log('已设置MutationObserver监听DOM变化');
        return observer;
    }
    
    // ==================== 初始化 ====================
    
    function init() {
        // 初始化配置
        initConfig();
        
        // API Hook
        hookXHR();
        hookFetch();
        hookWebSocket();
        hookWindowOpen();
        hookDocumentWrite();
        
        // DOM Hook
        // 等待DOM加载完成后处理现有元素
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                processAllElements();
                setupMutationObserver();
            });
        } else {
            processAllElements();
            setupMutationObserver();
        }
        
        utils.log('URL修正插件初始化完成');
    }
    
    // 启动插件
    init();
    
    // 返回公共API
    return {
        fixUrl: utils.fixUrl,
        processElement: processElement,
        processAllElements: processAllElements
    };
})();