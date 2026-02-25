"""
多功能 Telegram Bot 主程序

功能：天气预报 | 频道新闻 | AI 对话 | 视频下载 | 以图搜图
"""
import logging
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import config
from modules import weather, channel, chat, image_search, downloader, monitor
from modules.utils import lc7c, clean_ai_response, safe_reply, safe_edit

# 配置日志
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 过滤掉不必要的日志
for name in ['httpx', 'httpcore', 'telegram.ext', 'apscheduler', 'telethon', 'asyncio']:
    logging.getLogger(name).setLevel(logging.ERROR)

# 用户设置（内存存储）
user_settings = {}  # {user_id: {"model": str, "chat_mode": bool}}

def get_user_settings(user_id: int) -> dict:
    """获取用户设置（内存）"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "model": config.DEFAULT_MODEL,
            "chat_mode": False
        }
    return user_settings[user_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "靓仔"
    
    # 初始化用户设置
    get_user_settings(user_id)
    
    # 记录日志
    logger.info(f"[新用户] {user_name} (ID:{user_id}) 加入")
    
    welcome = f"""
🍆💦 **哟~ 是 {user_name} 啊！**
*Yooooo~ Look who's here, it's {user_name}!*

欢迎来到 **大鸡巴爱小嫩逼** 俱乐部！
*Welcome to the GiantCockLovePussy Club!*

你的大鸡巴已经准备好为你服务了 🐔
*Your GiantCock is ready to serve you* 🐔

别害羞，试试发个 /help 看看我有多能干~
*Don't be shy, try /help to see how capable I am~*
"""
    await safe_reply(update.message, lc7c(welcome), parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = """
📖 **命令帮助**

• `/image` - 以图搜图
• `/dl 链接` - 下载视频
• `/chat` - 和 AI 对话（Gemini、Claude）
• `/news` - 频道新闻

• `/weather` - 天气查询
• `/model` - 切换模型
• `/test` - 测试 AI 连接

有疑问？喊一声 Lc7c
Got any questions? Ask Lc7c directly!
"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌤 天气", callback_data="quick_weather"),
         InlineKeyboardButton("📰 新闻", callback_data="quick_news")],
        [InlineKeyboardButton("💬 AI 对话", callback_data="quick_chat"),
         InlineKeyboardButton("🤖 切换模型", callback_data="quick_model")],
    ])
    await safe_reply(update.message, lc7c(help_text), parse_mode='Markdown', reply_markup=keyboard)


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /weather 命令"""
    # 使用参数城市或默认城市
    if context.args:
        city = " ".join(context.args)
    else:
        city = config.DEFAULT_CITY
    
    await update.message.reply_text(f"🔍 正在获取 {city} 的天气...")
    report = await weather.get_weather_report(city)
    await safe_reply(update.message, lc7c(report), parse_mode='Markdown')


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /chat 命令"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    
    # 检查是否要关闭
    if context.args and context.args[0].lower() == "off":
        settings["chat_mode"] = False
        chat.reset_chat(user_id)
        await update.message.reply_text(lc7c("🔴 已退出 AI 对话模式"))
        return
    
    # 开启对话模式
    settings["chat_mode"] = True
    chat.reset_chat(user_id)  # 重置对话历史
    
    # 构建按钮
    keyboard = build_chat_keyboard()
    
    await update.message.reply_text(
        lc7c(f"🟢 已进入 AI 对话模式\n"
        f"当前模型: {settings['model']}\n"
        f"使用 /model 切换模型\n\n"
        f"直接发送消息开始对话"),
        reply_markup=keyboard
    )

def build_chat_keyboard() -> InlineKeyboardMarkup:
    """构建 Chat 功能的按钮键盘（只有退出按钮）"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 退出对话", callback_data="chat_off")]
    ])


async def chat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 Chat 相关的回调按钮"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # 退出对话
    if data == "chat_off":
        settings = get_user_settings(user_id)
        settings["chat_mode"] = False
        chat.reset_chat(user_id)
        await query.edit_message_text(lc7c("🔴 已退出 AI 对话模式"))
        return


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /model 命令 - 显示模型选择按钮"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    
    # 如果有参数，直接切换
    if context.args:
        new_model = context.args[0]
        if chat.is_valid_model(new_model):
            settings["model"] = new_model
            await safe_reply(update.message, lc7c(f"✅ 模型已切换为: `{new_model}`"), parse_mode='Markdown')
        else:
            await update.message.reply_text(lc7c(f"❌ 无效的模型名称: {new_model}"))
        return
    
    # 无参数，显示按钮选择
    buttons = []
    row = []
    for i, model in enumerate(config.AVAILABLE_MODELS):
        marker = "✓ " if model == settings["model"] else ""
        # 简化显示名称
        short_name = model.replace("gemini-", "G").replace("claude-", "C").replace("-thinking", "💭")
        row.append(InlineKeyboardButton(f"{marker}{short_name}", callback_data=f"model_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_reply(update.message, 
        lc7c(f"🤖 **选择模型**\n当前: `{settings['model']}`"),
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /test 命令 - 测试 AI 连接"""
    await update.message.reply_text("🔄 正在测试 AI API 连接...")
    
    success, message = await chat.test_connection()
    await update.message.reply_text(lc7c(message))


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理模型选择按钮"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    settings = get_user_settings(user_id)
    data = query.data
    
    # model_0, model_1, ...
    idx = int(data.split("_")[1])
    if idx < len(config.AVAILABLE_MODELS):
        new_model = config.AVAILABLE_MODELS[idx]
        settings["model"] = new_model
        await safe_edit(query, lc7c(f"✅ 模型已切换为: `{new_model}`"), parse_mode='Markdown')


async def quick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 快捷按钮"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "quick_weather":
        city = config.DEFAULT_CITY
        await query.edit_message_text(f"🔍 正在获取 {city} 的天气...")
        report = await weather.get_weather_report(city)
        await safe_edit(query, lc7c(report), parse_mode='Markdown')
    
    elif data == "quick_news":
        # 显示频道选择按钮
        buttons = []
        for i, ch in enumerate(config.NEWS_CHANNELS):
            buttons.append([
                InlineKeyboardButton(f"📰 {ch['name']} 今日", callback_data=f"news_ch_{i}_today"),
                InlineKeyboardButton(f"📋 最近30条", callback_data=f"news_ch_{i}_30")
            ])
        keyboard = InlineKeyboardMarkup(buttons)
        await safe_edit(query, lc7c("📰 **选择新闻频道**"), parse_mode='Markdown', reply_markup=keyboard)
    
    elif data == "quick_chat":
        settings = get_user_settings(user_id)
        settings["chat_mode"] = True
        chat.reset_chat(user_id)
        keyboard = build_chat_keyboard()
        await query.edit_message_text(
            lc7c(f"🟢 已进入 AI 对话模式\n"
            f"当前模型: {settings['model']}\n\n"
            f"直接发送消息开始对话"),
            reply_markup=keyboard
        )
    
    elif data == "quick_model":
        settings = get_user_settings(user_id)
        buttons = []
        row = []
        for i, model in enumerate(config.AVAILABLE_MODELS):
            marker = "✓ " if model == settings["model"] else ""
            short_name = model.replace("gemini-", "G").replace("claude-", "C").replace("-thinking", "💭")
            row.append(InlineKeyboardButton(f"{marker}{short_name}", callback_data=f"model_{i}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        keyboard = InlineKeyboardMarkup(buttons)
        await safe_edit(query, 
            lc7c(f"🤖 **选择模型**\n当前: `{settings['model']}`"),
            parse_mode='Markdown',
            reply_markup=keyboard
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /status 命令 - 手机状态（隐藏命令）"""
    status_text = monitor.get_status_text()
    await safe_reply(update.message, lc7c(status_text), parse_mode='Markdown')


async def net_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /net 命令 - 流量统计（隐藏命令）"""
    net_text = monitor.get_net_text()
    await safe_reply(update.message, lc7c(net_text), parse_mode='Markdown')

# 等待搜图的用户列表
waiting_for_image = set()

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /image 命令 - 以图搜图"""
    user_id = update.effective_user.id
    
    # 检查是否回复了一张图片
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        # 用户回复了一张图片，直接处理
        await process_image_search(update, update.message.reply_to_message)
        return
    
    # 标记用户等待发送图片
    waiting_for_image.add(user_id)
    
    await safe_reply(update.message, lc7c(
        "📷 **以图搜图**\n\n"
        "请发送一张图片，我将为你生成搜图链接\n\n"
        "支持的搜索引擎：\n"
        "• Google Lens\n"
        "• Yandex Images\n"
        "• Bing Visual\n"
        "• TinEye\n"
        "• SauceNAO (动漫)\n"
        "• IQDB (动漫)\n"
        "搜图平台可能会搜图失败\n"
        "\n"
        "此为一次性指令"
    ), parse_mode='Markdown')


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片消息"""
    user_id = update.effective_user.id
    
    # 检查用户是否在等待发送图片
    if user_id not in waiting_for_image:
        return  # 不处理非搜图请求的图片
    
    # 移除等待状态
    waiting_for_image.discard(user_id)
    
    await process_image_search(update, update.message)


async def process_image_search(update: Update, photo_message):
    """处理图片搜索"""
    await update.message.reply_text("🔍 正在处理图片...")
    
    try:
        # 获取最大分辨率的图片
        photo = photo_message.photo[-1]
        file = await photo.get_file()
        
        # 下载图片
        image_bytes = await file.download_as_bytearray()
        
        # 上传并获取链接
        success, result = await image_search.search_image(bytes(image_bytes))
        
        if success:
            # 使用新的按钮格式
            text, keyboard_data = image_search.build_search_result(result)
            
            # 构建 InlineKeyboardMarkup
            keyboard = []
            for row in keyboard_data:
                keyboard.append([
                    InlineKeyboardButton(btn["text"], url=btn["url"]) 
                    for btn in row
                ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.info(f"[搜图] 用户 {update.effective_user.id} 搜索成功")
            await safe_reply(update.message,
                lc7c(text), 
                parse_mode='Markdown', 
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(lc7c(result))
            
    except Exception as e:
        logger.error(f"搜图失败: {e}")
        await update.message.reply_text(lc7c(f"❌ 搜图失败: {str(e)[:100]}"))


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /dl 命令 - 下载视频"""
    if not context.args:
        supported_sites = "\n".join([f"• {name}" for name in set(downloader.SUPPORTED_SITES.values())])
        await update.message.reply_text(lc7c(
            "📥 **视频下载器**\n\n"
            "发送格式: `/dl <视频链接>`\n\n"
            "**支持的网站：**\n"
            f"{supported_sites}\n\n"
            "这个指令bug很多，但已知YouTube可用\n"
            "⚠️ tg原因，文件限制 50MB"
        ), parse_mode='Markdown')
        return
    
    url = context.args[0]
    
    # 检查是否支持
    site_name = downloader.get_site_name(url)
    if not site_name:
        await update.message.reply_text(lc7c("❌ 不支持的链接\n\n发送 /dl 查看支持的网站"))
        return
    
    # 发送处理中消息
    status_msg = await update.message.reply_text(f"📥 正在从 {site_name} 下载...\n⏳ 请稍候，可能需要几分钟")
    
    try:
        # 下载
        success, message, file_path = await downloader.download_video(url)
        
        if success and file_path:
            # 发送视频
            await status_msg.edit_text(f"📤 正在上传视频...")
            
            with open(file_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=lc7c(f"✅ 来自 {site_name}\n\n{message}"),
                    supports_streaming=True
                )
            
            await status_msg.delete()
            
            # 清理临时文件
            downloader.cleanup_file(file_path)
            logger.info(f"[下载] 用户 {update.effective_user.id} 下载成功: {url}")
        else:
            await status_msg.edit_text(lc7c(message))
            
    except Exception as e:
        logger.error(f"下载出错: {e}")
        await status_msg.edit_text(lc7c(f"❌ 下载出错: {str(e)[:100]}"))


# 缓存消息列表（用于翻页）
news_cache = {}

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /news 命令 - 频道消息功能
    
    用法：
    /news - 显示频道选择菜单
    /news 1 - 在华PD 今日消息
    /news 2 - 竹新社 今日消息
    /news 1 30 - 在华PD 最近30条
    """
    user_id = update.effective_user.id
    
    # 检查 Telethon 是否可用
    if not channel.telethon_client:
        await update.message.reply_text(lc7c("❌ 频道功能不可用\n请检查 TELEGRAM_API_ID 和 TELEGRAM_API_HASH 是否已配置"))
        return
    
    args = context.args
    
    # /news search 关键词
    if args and args[0].lower() == "search" and len(args) > 1:
        keyword = " ".join(args[1:])
        await update.message.reply_text(f"🔍 正在搜索: {keyword}...")
        
        messages = await channel.search_messages(keyword)
        if not messages:
            await update.message.reply_text(lc7c(f"😢 没有找到包含「{keyword}」的消息"))
            return
        
        news_cache[user_id] = {"messages": messages, "type": "search", "keyword": keyword}
        total_pages = channel.get_total_pages(messages)
        text = channel.format_messages_page(messages, 1, total_pages, f"搜索: {keyword}")
        
        keyboard = _build_page_keyboard(1, total_pages)
        await safe_reply(update.message, lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        return
    
    # /news 1 或 /news 2 或 /news 1 30 - 频道选择
    if args and args[0].isdigit():
        channel_idx = int(args[0]) - 1
        
        # 检查是否为有效频道索引
        if 0 <= channel_idx < len(config.NEWS_CHANNELS):
            ch = config.NEWS_CHANNELS[channel_idx]
            limit = 50
            today_only = True
            
            # 第二个参数是数量
            if len(args) > 1 and args[1].isdigit():
                limit = min(int(args[1]), 100)
                today_only = False
            
            status = "今日消息" if today_only else f"最近 {limit} 条"
            await update.message.reply_text(f"📰 正在获取 {ch['name']} {status}...")
            
            messages = await channel.get_messages(
                channel_username=ch["username"],
                limit=limit,
                today_only=today_only,
                has_title=ch["has_title"]
            )
            
            if not messages:
                await safe_reply(update.message, lc7c(f"📭 {ch['name']} 暂无消息\n\n💡 试试 `/news {channel_idx + 1} 30` 查看最近30条"), parse_mode='Markdown')
                return
            
            news_cache[user_id] = {"messages": messages, "type": "channel", "channel": ch}
            total_pages = channel.get_total_pages(messages)
            text = channel.format_messages_page(messages, 1, total_pages, f"{ch['name']} {status}")
            
            keyboard = _build_page_keyboard(1, total_pages)
            logger.info(f"[频道] {ch['name']} 获取到 {len(messages)} 条")
            await safe_reply(update.message, lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
            return
        else:
            # 数字太大，当作获取最近N条（默认频道）
            limit = min(int(args[0]), 100)
            await update.message.reply_text(f"📰 正在获取最近 {limit} 条消息...")
            
            messages = await channel.get_messages(limit=limit, today_only=False)
            news_cache[user_id] = {"messages": messages, "type": "recent", "limit": limit}
            total_pages = channel.get_total_pages(messages)
            text = channel.format_messages_page(messages, 1, total_pages, f"最近 {limit} 条消息")
            
            keyboard = _build_page_keyboard(1, total_pages)
            await safe_reply(update.message, lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
            return
    
    # /news - 显示频道选择按钮
    buttons = []
    for i, ch in enumerate(config.NEWS_CHANNELS):
        buttons.append([
            InlineKeyboardButton(f"📰 {ch['name']} 今日", callback_data=f"news_ch_{i}_today"),
            InlineKeyboardButton(f"� 最近30条", callback_data=f"news_ch_{i}_30")
        ])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        lc7c("📰 **选择新闻频道**"),
        parse_mode='Markdown',
        reply_markup=keyboard
    )


def _build_page_keyboard(current_page: int, total_pages: int):
    """构建翻页键盘"""
    if total_pages <= 1:
        return None
    
    buttons = []
    
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"news_page_{current_page - 1}"))
    
    buttons.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="news_noop"))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"news_page_{current_page + 1}"))
    
    return InlineKeyboardMarkup([buttons])


async def news_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理新闻相关按钮回调"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "news_noop":
        return
    
    # 频道选择按钮: news_ch_0_today 或 news_ch_1_30
    if data.startswith("news_ch_"):
        parts = data.split("_")
        channel_idx = int(parts[2])
        mode = parts[3]  # "today" 或 "30"
        
        if channel_idx >= len(config.NEWS_CHANNELS):
            await query.edit_message_text(lc7c("❌ 无效的频道"))
            return
        
        ch = config.NEWS_CHANNELS[channel_idx]
        today_only = (mode == "today")
        limit = 50 if today_only else 30
        status = "今日消息" if today_only else "最近 30 条"
        
        await query.edit_message_text(f"📰 正在获取 {ch['name']} {status}...")
        
        messages = await channel.get_messages(
            channel_username=ch["username"],
            limit=limit,
            today_only=today_only,
            has_title=ch["has_title"]
        )
        
        if not messages:
            await query.edit_message_text(lc7c(f"📭 {ch['name']} 暂无消息"))
            return
        
        news_cache[user_id] = {"messages": messages, "type": "channel", "channel": ch, "status": status}
        total_pages = channel.get_total_pages(messages)
        text = channel.format_messages_page(messages, 1, total_pages, f"{ch['name']} {status}")
        keyboard = _build_page_keyboard(1, total_pages)
        
        logger.info(f"[频道] {ch['name']} 获取到 {len(messages)} 条")
        await safe_edit(query, lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        return
    
    # 翻页按钮
    if not data.startswith("news_page_"):
        return
    
    page = int(data.split("_")[2])
    
    cache = news_cache.get(user_id)
    if not cache:
        await query.edit_message_text(lc7c("❌ 消息已过期，请重新发送 /news"))
        return
    
    messages = cache["messages"]
    total_pages = channel.get_total_pages(messages)
    
    # 构建标题
    if cache["type"] == "search":
        title = f"搜索: {cache['keyword']}"
    elif cache["type"] == "channel":
        title = f"{cache['channel']['name']} {cache.get('status', '')}"
    elif cache["type"] == "recent":
        title = f"最近 {cache['limit']} 条消息"
    else:
        title = f"@{config.TARGET_CHANNEL} 今日消息"
    
    text = channel.format_messages_page(messages, page, total_pages, title)
    keyboard = _build_page_keyboard(page, total_pages)
    
    await safe_edit(query, lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通文本消息"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    
    # 检查是否在对话模式
    if not settings["chat_mode"]:
        return  # 不在对话模式，忽略消息
    
    user_message = update.message.text
    user_name = update.effective_user.first_name or "用户"
    
    # 记录收到的消息
    logger.info(f"[AI收到] {user_name}: {user_message}")
    
    # 构建按钮
    keyboard = build_chat_keyboard()
    
    # 发送"正在思考"占位消息
    thinking_msg = await update.message.reply_text(
        lc7c("🤔 AI 正在思考..."),
        reply_markup=keyboard
    )
    
    # 发送"正在输入"状态
    await update.message.chat.send_action("typing")
    
    try:
        # 在后台线程调用 AI（避免阻塞事件循环）
        response = await asyncio.to_thread(
            chat.chat,
            [{"role": "user", "content": user_message}],
            settings["model"],
            user_id
        )
        
        # 记录 AI 回复（限制长度防止终端溢出）
        log_response = response.replace('\n', ' ')[:200]
        logger.info(f"[AI回复] {log_response}{'...' if len(response) > 200 else ''}")
        
        # 清理 Markdown 符号
        clean_response = clean_ai_response(response)
        
        # 编辑"思考中"消息为实际回复
        if len(clean_response) > 4000:
            # 长消息：编辑思考消息为第一段，后续分段发送新消息
            parts = [clean_response[i:i+4000] for i in range(0, len(clean_response), 4000)]
            # 第一段替换思考消息
            await thinking_msg.edit_text(lc7c(parts[0]))
            # 后续段发送新消息，最后一段加按钮
            for i, part in enumerate(parts[1:], 1):
                if i == len(parts) - 1:
                    await update.message.reply_text(lc7c(part), reply_markup=keyboard)
                else:
                    await update.message.reply_text(lc7c(part))
        else:
            await thinking_msg.edit_text(lc7c(clean_response), reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"AI 对话出错: {e}")
        error_msg = str(e)
        
        # 编辑"思考中"消息为错误信息
        if "容量不足" in error_msg or "不可用" in error_msg:
            await thinking_msg.edit_text(lc7c(f"❌ {error_msg}"), reply_markup=keyboard)
        elif "503" in error_msg or "unhealthy" in error_msg.lower():
            await thinking_msg.edit_text(lc7c("❌ AI 服务不可用\n请确保 Antigravity Manager 正在运行"), reply_markup=keyboard)
        elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            await thinking_msg.edit_text(lc7c("❌ AI 响应超时，请重试"), reply_markup=keyboard)
        else:
            await thinking_msg.edit_text(lc7c(f"❌ 对话出错: {error_msg[:150]}"), reply_markup=keyboard)


async def post_init(application: Application):
    """应用初始化后的回调"""
    # 初始化 Telethon 客户端
    telethon = channel.init_telethon_client()
    if telethon:
        try:
            await telethon.start()
            logger.info("Telethon 客户端已启动")
        except Exception as e:
            logger.error(f"Telethon 启动失败: {e}")
    
    # 初始化 AI 客户端
    chat.init_client()
    logger.info("AI 客户端已初始化")
    
    # 初始化手机监控（仅 Termux 环境）
    if monitor.IS_TERMUX:
        monitor.init_monitor()
        
        # 创建发送警报的函数
        async def send_monitor_alert(message: str):
            # 发送给所有已知用户
            for uid in list(user_settings.keys()):
                try:
                    await application.bot.send_message(
                        chat_id=uid,
                        text=lc7c(message),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"发送监控警报失败: {e}")
        
        # 启动监控循环
        import asyncio
        asyncio.create_task(monitor.monitor_loop(send_monitor_alert))
        logger.info("手机监控已启动")

async def post_shutdown(application: Application):
    """应用关闭时的回调"""
    if channel.telethon_client:
        await channel.telethon_client.disconnect()
        logger.info("Telethon 客户端已断开")


def main():
    """主函数"""
    print("🤖 正在启动多功能 Bot...")
    
    # 创建 Application
    application = Application.builder().token(config.BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    
    # 添加命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("chat", chat_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CommandHandler("dl", download_command))
    # 隐藏命令（不在 /help 显示）
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("net", net_command))
    
    # 添加图片消息处理器（用于 /image 搜图）
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # 添加回调查询处理器
    application.add_handler(CallbackQueryHandler(news_callback, pattern="^news_"))
    application.add_handler(CallbackQueryHandler(chat_callback, pattern="^chat_off$"))
    application.add_handler(CallbackQueryHandler(model_callback, pattern="^model_"))
    application.add_handler(CallbackQueryHandler(quick_callback, pattern="^quick_"))
    
    # 添加消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 添加错误处理器
    async def error_handler(update, context):
        logger.error(f"Bot 错误: {context.error}")
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot 已启动")
    
    # 启动
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
