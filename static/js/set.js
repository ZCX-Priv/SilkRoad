// 默认搜索引擎列表
var se_list_preinstall = {
    '1': {
        id: 1,
        title: "百度",
        url: "/https://www.baidu.com/s",
        name: "wd",
        icon: "iconfont icon-baidu",
    },
    '2': {
        id: 2,
        title: "必应",
        url: "/https://cn.bing.com/search",
        name: "q",
        icon: "iconfont icon-bing",
    },
    '3': {
        id: 3,
        title: "Yandex",
        url: "/https://yandex.com/search/",
        name: "text",
        icon: "iconfont-exp icon-yandex",
    },
    '4': {
        id: 4,
        title: "搜狗",
        url: "/https://www.sogou.com/web",
        name: "query",
        icon: "iconfont icon-sougousousuo",
    },
    '5': {
        id: 5,
        title: "360",
        url: "/https://www.so.com/s",
        name: "q",
        icon: "iconfont icon-360sousuo",
    },
    '6': {
        id: 6,
        title: "夸克",
        url: "/https://s.quark.cn/s",
        name: "q",
        icon: "iconfont-exp icon-kuake",
    },
    '7': {
        id: 7,
        title: "网址",
        url: "/",
        name: "url",
        icon: "iconfont-exp icon-URLguanli",
    }
};

// 默认快捷方式
var quick_list_preinstall = {
    '1': {
        title: "AI助手",
        url: "/chat",
        proxy: false,
    },
    '2': {
        title: "班级网盘",
        url: "http://192.168.40.101/",
        proxy: false,
    },
    '3': {
        title: "每日一图",
        url: "http://192.168.40.101/工具/每日一图/index.html",
        proxy: false,
    },
    '4': {
        title: "虎扑社区",
        url: "https://www.hupu.com/",
        proxy: true,
    },
    '5': {
        title: "海螺聆听",
        url: "https://qtings.com/",
        proxy: false,
    },
};

// 处理URL，根据代理设置添加代理前缀
function processUrl(url, useProxy) {
    // 如果不使用代理或URL已经有代理前缀或是相对路径，则不做处理
    if (!useProxy || url.startsWith('/http') || url.startsWith('./') || url.startsWith('/')) {
        return url;
    }
    // 添加代理前缀
    return '/' + url;
}

// 获取搜索引擎列表
function getSeList() {
    var se_list_local = Cookies.get('se_list');
    if (se_list_local !== "{}" && se_list_local) {
        return JSON.parse(se_list_local);
    } else {
        setSeList(se_list_preinstall);
        return se_list_preinstall;
    }
}

// 设置搜索引擎列表
function setSeList(se_list) {
    if (se_list) {
        Cookies.set('se_list', se_list, {
            expires: 36500
        });
        return true;
    }
    return false;
}

// 获得默认搜索引擎
function getSeDefault() {
    var se_default = Cookies.get('se_default');
    return se_default ? se_default : "1";
}

//背景图片
var bg_img_preinstall = {
    "type": "1", // 1:使用主题默认的背景图片 2:必应每日 3:随机风景 4:随机二次元 5:自定义
    "path": "", //自定义图片
};

// 获取背景图片
function getBgImg() {
    var bg_img_local = Cookies.get('bg_img');
    if (bg_img_local && bg_img_local !== "{}") {
        return JSON.parse(bg_img_local);
    } else {
        setBgImg(bg_img_preinstall);
        return bg_img_preinstall;
    }
}

// 设置背景图片
function setBgImg(bg_img) {
    if (bg_img) {
        Cookies.set('bg_img', bg_img, {
            expires: 36500
        });
        return true;
    }
    return false;
}
// 保存当前壁纸到localStorage（将图片内容转为Base64）
function saveCurrentWallpaper(url) {
    // 创建一个新的Image对象
    var img = new Image();
    img.crossOrigin = "Anonymous";  // 解决跨域问题
    
    img.onload = function() {
        try {
            // 创建canvas并绘制图片
            var canvas = document.createElement("canvas");
            canvas.width = img.width;
            canvas.height = img.height;
            var ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0);
            
            // 将图片转换为Base64格式的JPEG
            var dataURL = canvas.toDataURL("image/jpeg", 0.8);
            
            // 创建JSON对象存储壁纸信息
            var wallpaperData = {
                dataURL: dataURL,
                originalURL: url,
                timestamp: new Date().getTime()
            };
            
            // 存储到localStorage
            localStorage.setItem('current_wallpaper', JSON.stringify(wallpaperData));
            console.log("壁纸内容已保存到localStorage");
        } catch (e) {
            // 如果转换失败，至少保存URL
            console.error("保存壁纸内容失败：", e);
            localStorage.setItem('current_wallpaper_url', url);
        }
    };
    
    img.onerror = function() {
        // 如果加载失败，保存URL作为备选
        console.error("加载壁纸图片失败");
        localStorage.setItem('current_wallpaper_url', url);
    };
    
    // 设置图片源
    img.src = url;
}

// 从localStorage获取当前壁纸
function getCurrentWallpaper() {
    // 尝试获取存储的壁纸数据
    var wallpaperData = localStorage.getItem('current_wallpaper');
    
    if (wallpaperData) {
        try {
            // 解析JSON数据
            var data = JSON.parse(wallpaperData);
            return data.dataURL;  // 返回Base64数据
        } catch (e) {
            console.error("解析壁纸数据失败：", e);
        }
    }
    
    // 如果没有找到壁纸数据或解析失败，尝试获取URL
    var wallpaperURL = localStorage.getItem('current_wallpaper_url');
    if (wallpaperURL) {
        return wallpaperURL;
    }
    
    // 如果都没有，尝试从Cookie中获取（兼容旧版本）
    return Cookies.get('current_wallpaper');
}

// 设置-壁纸
function setBgImgInit() {
    var bg_img = getBgImg();
    $("input[name='wallpaper-type'][value=" + bg_img["type"] + "]").click();
    if (bg_img["type"] === "5") {
        $("#wallpaper-url").val(bg_img["path"]);
        $("#wallpaper-button").fadeIn(100);
        $("#wallpaper_url").fadeIn(100);
    } else {
        $("#wallpaper_url").fadeOut(300);
        $("#wallpaper-button").fadeOut(300);
    }

    var wallpaperUrl = "";
    
    switch (bg_img["type"]) {
        case "1":
            var pictures = new Array();
            pictures[0] = './static/img/background1.webp';
            pictures[1] = './static/img/background2.webp';
            pictures[2] = './static/img/background3.webp';
            pictures[3] = './static/img/background4.webp';
            pictures[4] = './static/img/background5.webp';
            pictures[5] = './static/img/background6.webp';
            pictures[6] = './static/img/background7.webp';
            pictures[7] = './static/img/background8.webp';
            pictures[8] = './static/img/background9.webp';
            pictures[9] = './static/img/background10.webp';
            var rd = Math.floor(Math.random() * 10);
            wallpaperUrl = pictures[rd];
            $('#bg').attr('src', wallpaperUrl); //随机默认壁纸
            break;
        case "2":
            wallpaperUrl = '/https://api.dujin.org/bing/1920.php';
            $('#bg').attr('src', wallpaperUrl); //必应每日
            break;
        case "3":
            wallpaperUrl = '/https://tu.ltyuanfang.cn/api/fengjing.php';
            $('#bg').attr('src', wallpaperUrl); //随机风景
            break;
        case "4":
            wallpaperUrl = '/https://www.dmoe.cc/random.php';
            $('#bg').attr('src', wallpaperUrl); //随机二次元
            break;
        case "5":
            wallpaperUrl = bg_img["path"];
            $('#bg').attr('src', wallpaperUrl); //自定义
            break;
    }
    
    // 监听图片加载完成事件，获取实际显示的图片URL
    $('#bg').on('load', function() {
        // 获取实际显示的图片URL（可能经过重定向）
        var actualUrl = $(this).attr('src');
        // 保存实际URL和图片内容到localStorage
        saveCurrentWallpaper(actualUrl);
        console.log("保存壁纸到localStorage：" + actualUrl); // 添加调试信息
    });
}

// 搜索框高亮
function focusWd() {
    $("body").addClass("onsearch");
}

// 搜索框取消高亮
function blurWd() {
    $("body").removeClass("onsearch");
    //隐藏输入
    $(".wd").val("");
    //隐藏搜索建议
    $("#keywords").hide();
}

// 搜索建议提示
function keywordReminder() {
    var keyword = $(".wd").val();
    if (keyword != "") {
        $.ajax({
            url: '/https://suggestion.baidu.com/su?wd=' + keyword,
            dataType: 'jsonp',
            jsonp: 'cb', //回调函数的参数名(键值)key
            success: function (data) {
                //获取宽度
                $("#keywords").css("width", $('.sou').width());
                $("#keywords").empty().show();
                $.each(data.s, function (i, val) {
                    $('#keywords').append(`<div class="keyword" data-id="${i + 1}"><i class='iconfont icon-sousuo'></i>${val}</div>`);
                });
                $("#keywords").attr("data-length", data.s["length"]);
                $(".keyword").click(function () {
                    $(".wd").val($(this).text());
                    $("#search-submit").click();
                });
            },
            error: function () {
                $("#keywords").empty().show();
                $("#keywords").hide();
            }
        })
    } else {
        $("#keywords").empty().show();
        $("#keywords").hide();
    }
}

// 搜索框数据加载
function searchData() {
    var se_default = getSeDefault();
    var se_list = getSeList();
    var defaultSe = se_list[se_default];
    if (defaultSe) {
        // 确保URL有代理前缀
        var url = defaultSe["url"];
        if (url !== "/" && !url.startsWith("/")) {
            url = "/" + url;
        }
        $(".search").attr("action", url);
        $("#icon-se").attr("class", defaultSe["icon"]);
        $(".wd").attr("name", defaultSe["name"]);
    }

    // 判断窗口大小，添加输入框自动完成
    // var wid = $("body").width();
    // if (wid < 640) {
    //     $(".wd").attr('autocomplete', 'off');
    // } else {
    //     $(".wd").focus();
    //     focusWd();
    // }
}

// 搜索引擎列表加载
function seList() {
    var html = "";
    var se_list = getSeList();
    for (var i in se_list) {
        // 确保URL有代理前缀
        var url = se_list[i]["url"];
        if (url !== "/" && !url.startsWith("/")) {
            url = "/" + url;
        }
        html += `<div class='se-li' data-url='${url}' data-name='${se_list[i]["name"]}' data-icon='${se_list[i]["icon"]}'>
        <a class='se-li-text'><i id='icon-sou-list' class='${se_list[i]["icon"]}'></i><span>${se_list[i]["title"]}</span></a></div>`;
    }
    $(".search-engine-list").html(html);
}

// 设置-搜索引擎列表加载
function setSeInit() {
    var se_default = getSeDefault();
    var se_list = getSeList();
    var html = "";
    for (var i in se_list) {
        var tr = `<div class='se_list_div'><div class='se_list_num'>${i}</div>`;
        if (i === se_default) {
            tr = `<div class='se_list_div'><div class='se_list_num'>
            <i class='iconfont icon-home'></i></div>`;
        }
        tr += `<div class='se_list_name'>${se_list[i]["title"]}</div>
        <div class='se_list_button'>
        <button class='set_se_default' value='${i}' style='border-radius: 8px 0px 0px 8px;'>
        <i class='iconfont icon-home'></i></button>
        <button class='edit_se' value='${i}'>
        <i class='iconfont icon-xiugai'></i></button>
        <button class='delete_se' value='${i}' style='border-radius: 0px 8px 8px 0px;'>
        <i class='iconfont icon-delete'></i></button></div>
        </div>`;
        html += tr;
    }
    $(".se_list_table").html(html);
}

// 获取快捷方式列表
function getQuickList() {
    var quick_list_local = Cookies.get('quick_list');
    if (quick_list_local !== "{}" && quick_list_local) {
        return JSON.parse(quick_list_local);
    } else {
        setQuickList(quick_list_preinstall);
        return quick_list_preinstall;
    }
}

// 设置快捷方式列表
function setQuickList(quick_list) {
    if (quick_list) {
        Cookies.set('quick_list', quick_list, {
            expires: 36500
        });
        return true;
    }
    return false;
}

// 快捷方式数据加载
function quickData() {
    var html = "";
    var quick_list = getQuickList();
    for (var i in quick_list) {
        var processedUrl = processUrl(quick_list[i]['url'], quick_list[i]['proxy'] !== false);
        html += `<div class="quick">
                    <a href="${processedUrl}">${quick_list[i]['title']}</a>
                </div>`;
    }
    $(".quick-all").html(html + `<div class="quick"><a id="set-quick"><i class="iconfont icon-tianjia-"></i></a></div>`);
}

// 设置-快捷方式加载
function setQuickInit() {
    var quick_list = getQuickList();
    var html = "";
    for (var i in quick_list) {
        var proxyChecked = quick_list[i]['proxy'] !== false ? 'checked' : '';
        tr = `
        <div class='quick_list_div'>
            <div class='quick_list_div_num'>${i}</div>
            <div class='quick_list_div_name'>${quick_list[i]['title']}</div>
            <div class='quick_list_div_button'>
                <button class='edit_quick' value='${i}' style='border-radius: 8px 0px 0px 8px;'>
                <i class='iconfont icon-xiugai'></i></button>
                <button class='delete_quick' value='${i}' style='border-radius: 0px 8px 8px 0px;'>
                <i class='iconfont icon-delete'></i></button>
            </div>
        </div>`;
        html += tr;
    }
    $(".quick_list_table").html(html);
    
    // 添加代理开关事件监听
    $(".proxy_checkbox").change(function() {
        var key = $(this).val();
        var quick_list = getQuickList();
        quick_list[key]['proxy'] = $(this).prop('checked');
        setQuickList(quick_list);
    });
}

/**
 * 下载文本为文件
 * @param filename 文件名
 * @param text     内容
 */
function download(filename, text) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}

// 打开设置
function openSet() {
    $("#menu").addClass('on');

    openBox();

    //更改设置图标
    $("#icon-menu").attr("class", "iconfont icon-home");

    //隐藏书签打开设置
    $(".mark").css({
        "display": "none",
    });
    $(".set").css({
        "display": "flex",
    });
}

// 关闭设置
function closeSet() {
    $("#menu").removeClass('on');

    closeBox();

    //更改设置图标
    $("#icon-menu").attr("class", "iconfont icon-shezhi");

    //隐藏设置
    $(".set").css({
        "display": "none",
    });

    // 刷新主页数据
    seList();
    quickData();
}

// 书签显示
function openBox() {
    $("#content").addClass('box');
    $(".mark").css({
        "display": "flex",
    });
    //时间上移
    $(".tool-all").css({
        "transform": 'translateY(-160%)'
    });
    //背景模糊
    $('#bg').css({
        "transform": 'scale(1.08)',
        "filter": "blur(10px)",
        "transition": "ease 0.3s",
    });
}

// 书签关闭
function closeBox() {
    $("#content").removeClass('box');
    $(".mark").css({
        "display": "none",
    });
    //时间下移
    $(".tool-all").css({
        "transform": 'translateY(-120%)'
    });
    //背景模糊
    $('#bg').css({
        "transform": 'scale(1)',
        "filter": "blur(0px)",
        "transition": "ease 0.3s",
    });
}

//显示设置搜索引擎列表
function showSe() {
    $(".se_list").show();
    $(".se_add_preinstall").show();
}

//隐藏设置搜索引擎列表
function hideSe() {
    $(".se_list").hide();
    $(".se_add_preinstall").hide();
}

//显示设置快捷方式列表
function showQuick() {
    $(".quick_list").show();
    $(".se_add_preinstalls").show();
}

//隐藏设置快捷方式列表
function hideQuick() {
    $(".quick_list").hide();
    $(".se_add_preinstalls").hide();
}


$(document).ready(function () {

    // 搜索框数据加载
    searchData();

    // 搜索引擎列表加载
    seList();

    // 快捷方式数据加载
    quickData();

    // 壁纸数据加载
    setBgImgInit();

    // 点击事件
    $(document).on('click', function (e) {
        // 选择搜索引擎点击
        if ($(".search-engine").is(":hidden") && $(".se").is(e.target) || $(".search-engine").is(":hidden") && $("#icon-se").is(e.target)) {
            if ($(".se").is(e.target) || $("#icon-se").is(e.target)) {
                //获取宽度
                $(".search-engine").css("width", $('.sou').width() - 30);
                //出现动画
                $(".search-engine").slideDown(160);
            }
        } else {
            if (!$(".search-engine").is(e.target) && $(".search-engine").has(e.target).length === 0) {
                $(".search-engine").slideUp(160);
            }
        }

        // 自动提示隐藏
        if (!$(".sou").is(e.target) && $(".sou").has(e.target).length === 0) {
            $("#keywords").hide();
        }
    });

    // 时间点击
    $("#time_text").click(function () {
        if ($("#content").attr("class") === "box") {
            closeBox();
            closeSet();
            blurWd();
        } else {
            openBox();
        }
    });

    // 搜索引擎列表点击
    $(".search-engine-list").on("click", ".se-li", function () {
        var url = $(this).attr('data-url');
        // 确保URL有代理前缀
        if (url !== "/" && !url.startsWith("/")) {
            url = "/" + url;
        }
        var name = $(this).attr('data-name');
        var icon = $(this).attr('data-icon');
        $(".search").attr("action", url);
        $(".wd").attr("name", name);
        $("#icon-se").attr("class", icon);
        $(".search-engine").slideUp(160);
    });

    // 搜索框点击事件
    $(document).on('click', '.sou', function () {
        focusWd();
        $(".search-engine").slideUp(160);
    });

    $(document).on('click', '.wd', function () {
        focusWd();
        keywordReminder();
        $(".search-engine").slideUp(160);
    });

    // 点击其他区域关闭事件
    $(document).on('click', '.close_sou', function () {
        blurWd();
        closeSet();
    });

    // 点击搜索引擎时隐藏自动提示
    $(document).on('click', '.se', function () {
        $('#keywords').toggle();
    });

    // 恢复自动提示
    $(document).on('click', '.se-li', function () {
        $('#keywords').show();
    });

    // 自动提示 (调用百度 api）
    $('.wd').keyup(function (event) {
        var key = event.keyCode;
        // 屏蔽上下键
        var shieldKey = [38, 40];
        if (shieldKey.includes(key)) return;
        keywordReminder();
    });

    // 点击自动提示的搜索建议
    $("#keywords").on("click", ".wd", function () {
        var wd = $(this).text();
        $(".wd").val(wd);
        $(".search").submit();
        //隐藏输入
        $(".wd").val("");
        $("#keywords").hide();
    });

    // 自动提示键盘方向键选择操作
    $(".wd").keydown(function (event) { //上下键获取焦点
        var key = event.keyCode;
        if ($.trim($(this).val()).length === 0) return;

        var id = $(".choose").attr("data-id");
        if (id === undefined) id = 0;

        if (key === 38) {
            /*向上按钮*/
            id--;
        } else if (key === 40) {
            /*向下按钮*/
            id++;
        } else {
            return;
        }
        var length = $("#keywords").attr("data-length");
        if (id > length) id = 1;
        if (id < 1) id = length;

        $(".keyword[data-id=" + id + "]").addClass("choose").siblings().removeClass("choose");
        $(".wd").val($(".keyword[data-id=" + id + "]").text());
    });

    // 菜单点击
    $("#menu").click(function () {
        if ($(this).attr("class") === "on") {
            closeSet();
        } else {
            openSet();

            // 设置内容加载
            setSeInit(); //搜索引擎设置
            setQuickInit(); //快捷方式设置
        }
    });

    // 快捷方式添加按钮点击
   $(document).on('click', '#set-quick', function () {
        openSet();

        // 设置内容加载
        setSeInit(); //搜索引擎设置
        setQuickInit(); //快捷方式设置

        //添加快捷方式
        $("#set-quick-menu").trigger('click');
        $(".set_quick_list_add").trigger('click');
    });

    // 修改默认搜索引擎
    $(".se_list_table").on("click", ".set_se_default", function () {
        var name = $(this).val();
        Cookies.set('se_default', name, {
            expires: 36500
        });
        iziToast.show({
            timeout: 8000,
            message: '是否设置为默认搜索引擎？',
            buttons: [
                ['<button>确认</button>', function (instance, toast) {
                    setSeInit();
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                    iziToast.show({
                        message: '设置成功'
                    });
                    setTimeout(function () {
                        window.location.reload()
                    }, 1000);
                }, true],
                ['<button>取消</button>', function (instance, toast) {
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                }]
            ]
        });
    });

    // 搜索引擎添加
    $(".set_se_list_add").click(function () {
        $(".se_add_content input").val("");

        hideSe();
        $(".se_add_content").show();
    });

    // 搜索引擎保存
    $(".se_add_save").click(function () {
        var key_inhere = $(".se_add_content input[name='key_inhere']").val();
        var key = $(".se_add_content input[name='key']").val();
        var title = $(".se_add_content input[name='title']").val();
        var url = $(".se_add_content input[name='url']").val();
        var name = $(".se_add_content input[name='name']").val();
        //var icon = $(".se_add_content input[name='icon']").val();
        var icon = "iconfont icon-wangluo";
        // 确保URL有代理前缀（除了特殊URL如"/"）
        if (url !== "/" && !url.startsWith("/")) {
            url = "/" + url;
        }


        var num = /^\+?[1-9][0-9]*$/;
        if (!num.test(key)) {
            iziToast.show({
                timeout: 2000,
                message: '序号 ' + key + ' 不是正整数'
            });
            return;
        }

        var se_list = getSeList();

        if (se_list[key]) {
            iziToast.show({
                timeout: 8000,
                message: '搜索引擎 ' + key + ' 已有数据，是否覆盖？',
                buttons: [
                    ['<button>确认</button>', function (instance, toast) {
                        se_list[key] = {
                            title: title,
                            url: url,
                            name: name,
                            icon: icon,
                        };
                        setSeList(se_list);
                        setSeInit();
                        $(".se_add_content").hide();
                        //显示列表
                        showSe();

                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                        iziToast.show({
                            message: '覆盖成功'
                        });
                    }, true],
                    ['<button>取消</button>', function (instance, toast) {
                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                    }]
                ]
            });
            return;
        }

        if (key_inhere && key !== key_inhere) {
            delete se_list[key_inhere];
        }

        se_list[key] = {
            title: title,
            url: url,
            name: name,
            icon: icon,
        };
        setSeList(se_list);
        setSeInit();
        iziToast.show({
            timeout: 2000,
            message: '添加成功'
        });
        $(".se_add_content").hide();
        showSe();
    });

    // 关闭表单
    $(".se_add_cancel").click(function () {
        $(".se_add_content").hide();

        //显示列表
        showSe();
    });

    // 搜索引擎修改
    $(".se_list").on("click", ".edit_se", function () {

        var se_list = getSeList();
        var key = $(this).val();
        $(".se_add_content input[name='key_inhere']").val(key);
        $(".se_add_content input[name='key']").val(key);
        $(".se_add_content input[name='title']").val(se_list[key]["title"]);
        $(".se_add_content input[name='url']").val(se_list[key]["url"]);
        $(".se_add_content input[name='name']").val(se_list[key]["name"]);
        // $(".se_add_content input[name='icon']").val("iconfont icon-Earth");

        //隐藏列表
        hideSe();

        $(".se_add_content").show();
    });

    // 搜索引擎删除
    $(".se_list").on("click", ".delete_se", function () {
        var se_default = getSeDefault();
        var key = $(this).val();
        if (key == se_default) {
            iziToast.show({
                message: '默认搜索引擎不可删除'
            });
        } else {
            iziToast.show({
                timeout: 8000,
                message: '搜索引擎 ' + key + ' 是否删除？',
                buttons: [
                    ['<button>确认</button>', function (instance, toast) {
                        var se_list = getSeList();
                        delete se_list[key];
                        setSeList(se_list);
                        setSeInit();
                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                        iziToast.show({
                            message: '删除成功'
                        });
                    }, true],
                    ['<button>取消</button>', function (instance, toast) {
                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                    }]
                ]
            });
        }
    });

    // 恢复预设搜索引擎
    $(".set_se_list_preinstall").click(function () {
        iziToast.show({
            timeout: 8000,
            message: '现有搜索引擎数据将被清空',
            buttons: [
                ['<button>确认</button>', function (instance, toast) {
                    setSeList(se_list_preinstall);
                    Cookies.set('se_default', 1, {
                        expires: 36500
                    });
                    setSeInit();
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                    iziToast.show({
                        message: '重置成功'
                    });
                    setTimeout(function () {
                        window.location.reload()
                    }, 1000);
                }, true],
                ['<button>取消</button>', function (instance, toast) {
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                }]
            ]
        });
    });

    // 设置-快捷方式添加
    $(".set_quick_list_add").click(function () {
        $(".quick_add_content input").val("");
        $(".quick_add_content").show();

        //隐藏列表
        hideQuick();
    });

    // 设置-快捷方式保存
    $(".quick_add_save").click(function () {
        var key_inhere = $(".quick_add_content input[name='key_inhere']").val();
        var key = $(".quick_add_content input[name='key']").val();
        var title = $(".quick_add_content input[name='title']").val();
        var url = $(".quick_add_content input[name='url']").val();
        var img = $(".quick_add_content input[name='img']").val();
        var proxy = $(".quick_add_content input[name='proxy']").prop('checked');

        var num = /^\+?[1-9][0-9]*$/;
        if (!num.test(key)) {
            iziToast.show({
                timeout: 2000,
                message: '快捷方式 ' + key + ' 不是正整数'
            });
            return;
        }

        var quick_list = getQuickList();

        if (quick_list[key]) {
            iziToast.show({
                timeout: 8000,
                message: '快捷方式 " + key + " 已有数据，是否覆盖？',
                buttons: [
                    ['<button>确认</button>', function (instance, toast) {
                        quick_list[key] = {
                            title: title,
                            url: url,
                            img: img,
                            proxy: proxy,
                        };
                        setQuickList(quick_list);
                        setQuickInit();
                        $(".quick_add_content").hide();
                        //显示列表
                        showQuick();

                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                        iziToast.show({
                            message: '覆盖成功'
                        });
                    }, true],
                    ['<button>取消</button>', function (instance, toast) {
                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                    }]
                ]
            });
            return;
        }

        if (key_inhere && key != key_inhere) {
            delete quick_list[key_inhere];
        }

        quick_list[key] = {
            title: title,
            url: url,
            img: img,
        };
        setQuickList(quick_list);
        setQuickInit();
        $(".quick_add_content").hide();
        iziToast.show({
            timeout: 2000,
            message: '添加成功'
        });

        //显示列表
        showQuick();
    });

    // 设置-快捷方式关闭添加表单
    $(".quick_add_cancel").click(function () {
        $(".quick_add_content").hide();

        //显示列表
        showQuick();
    });

    //恢复预设快捷方式
    $(".set_quick_list_preinstall").click(function () {
        iziToast.show({
            timeout: 8000,
            message: '快捷方式数据将被清空',
            buttons: [
                ['<button>确认</button>', function (instance, toast) {
                    setQuickList(quick_list_preinstall);
                    setQuickInit();
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                    iziToast.show({
                        timeout: 2000,
                        message: '重置成功'
                    });
                    // setTimeout(function () {
                    //     window.location.reload()
                    // }, 1000);
                }, true],
                ['<button>取消</button>', function (instance, toast) {
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                }]
            ]
        });
    });

    // 快捷方式修改
    $(".quick_list").on("click", ".edit_quick", function () {

        var quick_list = getQuickList();
        var key = $(this).val();
        $(".quick_add_content input[name='key_inhere']").val(key);
        $(".quick_add_content input[name='key']").val(key);
        $(".quick_add_content input[name='title']").val(quick_list[key]["title"]);
        $(".quick_add_content input[name='url']").val(quick_list[key]["url"]);
        $(".quick_add_content input[name='img']").val(quick_list[key]["img"]);
        // 设置代理复选框状态，如果未定义则默认为true
        $("#quick_proxy").prop('checked', quick_list[key]["proxy"] !== false);
        //隐藏列表
        hideQuick();

        $(".quick_add_content").show();
    });

    // 快捷方式删除
    $(".quick_list").on("click", ".delete_quick", function () {

        var key = $(this).val();

        iziToast.show({
            timeout: 8000,
            message: '快捷方式 ' + key + ' 是否删除？',
            buttons: [
                ['<button>确认</button>', function (instance, toast) {
                    var quick_list = getQuickList();
                    delete quick_list[key];
                    setQuickList(quick_list);
                    setQuickInit();
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                    iziToast.show({
                        timeout: 2000,
                        message: '删除成功'
                    });
                }, true],
                ['<button>取消</button>', function (instance, toast) {
                    instance.hide({
                        transitionOut: 'flipOutX',
                    }, toast, 'buttonName');
                }]
            ]
        });
    });

    // 壁纸设置
    $("#wallpaper").on("click", ".set-wallpaper", function () {
        var type = $(this).val();
        var bg_img = getBgImg();
        bg_img["type"] = type;

        if (type === "1") {
            $('#wallpaper_text').html("显示默认壁纸，刷新页面以生效");
            setBgImg(bg_img);
            iziToast.show({
                message: '壁纸设置成功，刷新生效',
            });
        }

        if (type === "2") {
            $('#wallpaper_text').html("显示必应每日一图，每天更新，刷新页面以生效");
            setBgImg(bg_img);
            iziToast.show({
                message: '壁纸设置成功，刷新生效',
            });
        }

        if (type === "3") {
            $('#wallpaper_text').html("显示随机风景图，每次刷新后更换，刷新页面以生效");
            setBgImg(bg_img);
            iziToast.show({
                message: '壁纸设置成功，刷新生效',
            });
        }

        if (type === "4") {
            $('#wallpaper_text').html("显示随机二次元图，每次刷新后更换，刷新页面以生效");
            setBgImg(bg_img);
            iziToast.show({
                message: '壁纸设置成功，刷新生效',
            });
        }

        if (type === "5") {
            $('#wallpaper_text').html("自定义壁纸地址，请输入正确地址，点击保存且刷新页面以生效");
            $("#wallpaper_url").fadeIn(100);
            $("#wallpaper-button").fadeIn(100);
            $("#wallpaper-url").val(bg_img["path"]);
        } else {
            $("#wallpaper_url").fadeOut(300);
            $("#wallpaper-button").fadeOut(300);
        }
    });

    // 自定义壁纸设置保存
    $(".wallpaper_save").click(function () {
        var url = $("#wallpaper-url").val();
        var reg = /^http(s)?:\/\/(([\w-]+\.)+[\w-]|localhost)+(:[0-9]{1,5})?(\/[\w- ./?%&=]*)?$/g;
        if (!reg.test(url)) {
            iziToast.show({
                message: '请输入正确的链接',
            });
        } else {
            var bg_img = getBgImg();
            bg_img["type"] = "5";
            bg_img["path"] = url;
            setBgImg(bg_img);
            iziToast.show({
                message: '自定义壁纸设置成功，刷新生效',
            });
        }
    });

    // 我的数据导出
    $("#my_data_out").click(function () {
        var cookies = Cookies.get();
        var json = JSON.stringify(cookies);
        download("Snavigation-back-up-" + $.now() + ".json", json);
        iziToast.show({
            timeout: 2000,
            message: '已导出备份文件至下载目录'
        });
    });

    // 我的数据导入 点击触发文件选择
    $("#my_data_in").click(function () {
        $("#my_data_file").click();
    });

    // 选择文件后读取文件内容
    $("#my_data_file").change(function () {
        var selectedFile = document.getElementById('my_data_file').files[0];
        //var name = selectedFile.name;//读取选中文件的文件名
        //var size = selectedFile.size;//读取选中文件的大小
        //console.log("文件名:"+name+" 大小:"+size);

        var reader = new FileReader(); //这是核心,读取操作就是由它完成.
        reader.readAsText(selectedFile); //读取文件的内容,也可以读取文件的URL
        reader.onload = function () {
            //当读取完成后回调这个函数,然后此时文件的内容存储到了result中,直接操作即可
            //console.log(this.result);

            // json 格式校验
            var mydata;
            try {
                mydata = JSON.parse(this.result);
            } catch (e) {
                iziToast.show({
                    timeout: 2000,
                    message: '数据解析异常'
                });
                return;
            }
            if (typeof mydata != 'object') {
                iziToast.show({
                    timeout: 2000,
                    message: '数据格式错误'
                });
                return;
            }

            iziToast.show({
                timeout: 8000,
                message: '当前数据将会被覆盖！是否继续导入？',
                buttons: [
                    ['<button>确认</button>', function (instance, toast) {
                        for (var key in mydata) {
                            Cookies.set(key, mydata[key], {
                                expires: 36500
                            });
                        }
                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                        iziToast.show({
                            timeout: 2000,
                            message: '导入成功'
                        });
                        setTimeout(function () {
                            window.location.reload()
                        }, 1000);
                    }, true],
                    ['<button>取消</button>', function (instance, toast) {
                        instance.hide({
                            transitionOut: 'flipOutX',
                        }, toast, 'buttonName');
                        setTimeout(function () {
                            window.location.reload()
                        }, 1000);
                    }]
                ]
            });
        }
    });
});
