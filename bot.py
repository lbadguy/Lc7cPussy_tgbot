"""
多功能 Telegram Bot 主程序

功能：
1. 天气预报 - 每日 8:00 推送，/weather 指令
2. 频道汇总 - 每日 20:00 推送 @zaihuapd 消息汇总
3. AI 对话 - /chat 指令进入对话模式（需要反代服务）
"""
import asyncio
import logging
from datetime import time as dt_time, datetime, timedelta, timezone

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
from modules import weather, channel, chat, database, image_search

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 过滤掉 httpx 和 httpcore 的 INFO 日志（HTTP 200 OK 那些）
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

# 用户对话历史（内存存储，限制长度）
user_conversations = {}
MAX_HISTORY = 10


# ===== 常量和工具函数 =====

# Bot 标识前缀
BOT_PREFIX = "[ LC7c ]\n\n"

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))


def lc7c(text: str) -> str:
    """在消息前添加 Bot 标识前缀"""
    return BOT_PREFIX + text


def get_next_push_time(hour: int, minute: int = 0) -> str:
    """计算距离下次推送的时间"""
    now = datetime.now(CHINA_TZ)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if now >= target:
        target += timedelta(days=1)
    
    diff = target - now
    hours = int(diff.total_seconds() // 3600)
    minutes = int((diff.total_seconds() % 3600) // 60)
    
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    else:
        return f"{minutes}分钟"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "靓仔"
    
    # 添加订阅
    database.add_subscription(user_id)
    
    # 计算下次推送时间
    next_weather = get_next_push_time(8, 0)
    next_news = get_next_push_time(20, 0)
    
    # 记录日志
    logger.info(f"[新用户] {user_name} (ID:{user_id}) 加入了大鸡巴俱乐部")
    
    welcome = f"""
🍆💦 **哟~ 是 {user_name} 啊！**
*Ayyyy~ Look who's here, it's {user_name}!*

欢迎来到 **大鸡巴爱小嫩逼** 俱乐部！
*Welcome to the BigCockLovePussy Club!*

你的大鸡巴已经准备好为你服务了 🐔
*Your BigCock is ready to serve you* 🐔

别害羞，试试发个 /help 看看我有多能干~
*Don't be shy, try /help to see how capable I am~*

记住：鸡大者，得天下 🌍
*Remember: He who has the biggest cock, rules the world* 🌍

━━━━ **每日推送** ━━━━
⏰ 天气预报: 每日 8:00 和 20:00
    └ 下次推送: {next_weather}
📰 新闻汇总: 每日 20:00
    └ 下次推送: {next_news}
"""
    await update.message.reply_text(lc7c(welcome), parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = """
📖 **命令帮助**

**天气相关**
• `/weather` - 查看天气
• `/weather 北京` - 切换城市

**频道新闻**
• `/news` - 今日新闻
• `/news 30` - 最近30条
• `/news search 关键词` - 搜索

**以图搜图**
• `/image` - 发送图片搜图

**AI 对话**
• `/chat` - 开启对话
• `/chat off` - 关闭对话
• `/model` - 查看/切换模型

**其他**
• `/start` - 重新开始
• `/help` - 显示帮助
"""
    await update.message.reply_text(lc7c(help_text), parse_mode='Markdown')


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /weather 命令"""
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    
    # 检查是否有参数（设置新城市）
    if context.args:
        new_city = " ".join(context.args)
        # 验证城市是否存在
        city_info = await weather.search_city(new_city)
        if city_info:
            database.update_user_city(user_id, city_info["name"])
            await update.message.reply_text(f"✅ 城市已更新为: {city_info['name']}")
            # 显示新城市天气
            report = await weather.get_weather_report(city_info["name"])
            await update.message.reply_text(lc7c(report), parse_mode='Markdown')
        else:
            await update.message.reply_text(lc7c(f"❌ 未找到城市: {new_city}"))
    else:
        # 显示当前城市天气
        city = settings["city"]
        await update.message.reply_text(f"🔍 正在获取 {city} 的天气...")
        report = await weather.get_weather_report(city)
        await update.message.reply_text(lc7c(report), parse_mode='Markdown')


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /chat 命令"""
    user_id = update.effective_user.id
    
    # 检查是否要关闭
    if context.args and context.args[0].lower() == "off":
        database.update_chat_mode(user_id, False)
        if user_id in user_conversations:
            del user_conversations[user_id]
        await update.message.reply_text(lc7c("🔴 已退出 AI 对话模式"))
        return
    
    # 开启对话模式
    database.update_chat_mode(user_id, True)
    user_conversations[user_id] = []
    
    settings = database.get_user_settings(user_id)
    await update.message.reply_text(
        lc7c(f"🟢 已进入 AI 对话模式\n"
        f"当前模型: `{settings['model']}`\n\n"
        f"直接发送消息开始对话\n"
        f"使用 `/chat off` 退出"),
        parse_mode='Markdown'
    )


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /model 命令"""
    user_id = update.effective_user.id
    
    if context.args:
        new_model = context.args[0]
        if chat.is_valid_model(new_model):
            database.update_user_model(user_id, new_model)
            await update.message.reply_text(lc7c(f"✅ 模型已切换为: `{new_model}`"), parse_mode='Markdown')
        else:
            await update.message.reply_text(
                lc7c(f"❌ 无效的模型名称: {new_model}\n\n" + chat.get_model_list()),
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(lc7c(chat.get_model_list()), parse_mode='Markdown')


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /test 命令 - 测试 AI 连接"""
    await update.message.reply_text("🔄 正在测试 AI API 连接...")
    
    success, message = await chat.test_connection()
    await update.message.reply_text(lc7c(message))

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
    
    await update.message.reply_text(lc7c(
        "📷 **以图搜图**\n\n"
        "请发送一张图片，我将为你生成搜图链接\n\n"
        "支持的搜索引擎：\n"
        "• Google Lens\n"
        "• Yandex Images\n"
        "• Bing Visual\n"
        "• TinEye\n"
        "• SauceNAO (动漫)\n"
        "• IQDB (动漫)"
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
        
        # 搜索
        success, result = await image_search.search_image(bytes(image_bytes))
        
        if success:
            logger.info(f"[搜图] 用户 {update.effective_user.id} 搜索成功")
            await update.message.reply_text(lc7c(result), parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text(lc7c(result))
            
    except Exception as e:
        logger.error(f"搜图失败: {e}")
        await update.message.reply_text(lc7c(f"❌ 搜图失败: {str(e)[:100]}"))


# 缓存消息列表（用于翻页）
news_cache = {}

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /news 命令 - 频道消息功能"""
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
        await update.message.reply_text(lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        return
    
    # /news 数字 - 获取最近N条消息
    if args and args[0].isdigit():
        limit = min(int(args[0]), 100)
        await update.message.reply_text(f"📰 正在获取最近 {limit} 条消息...")
        
        messages = await channel.get_messages(limit=limit, today_only=False)
        news_cache[user_id] = {"messages": messages, "type": "recent", "limit": limit}
        total_pages = channel.get_total_pages(messages)
        text = channel.format_messages_page(messages, 1, total_pages, f"最近 {limit} 条消息")
        
        keyboard = _build_page_keyboard(1, total_pages)
        await update.message.reply_text(lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
        return
    
    # /news - 今日消息
    await update.message.reply_text("📰 正在获取今日消息...")
    
    messages = await channel.get_messages(today_only=True)
    if not messages:
        await update.message.reply_text(lc7c("📭 今日该频道暂无新消息\n\n💡 试试 `/news 30` 查看最近30条消息"), parse_mode='Markdown')
        return
    
    news_cache[user_id] = {"messages": messages, "type": "today"}
    total_pages = channel.get_total_pages(messages)
    text = channel.format_messages_page(messages, 1, total_pages, f"@{config.TARGET_CHANNEL} 今日消息")
    
    keyboard = _build_page_keyboard(1, total_pages)
    logger.info(f"[频道] 获取到 {len(messages)} 条消息")
    await update.message.reply_text(lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)


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
    """处理翻页按钮回调"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "news_noop":
        return
    
    if not data.startswith("news_page_"):
        return
    
    page = int(data.split("_")[2])
    
    # 获取缓存的消息
    cache = news_cache.get(user_id)
    if not cache:
        await query.edit_message_text(lc7c("❌ 消息已过期，请重新发送 /news"))
        return
    
    messages = cache["messages"]
    total_pages = channel.get_total_pages(messages)
    
    # 构建标题
    if cache["type"] == "search":
        title = f"搜索: {cache['keyword']}"
    elif cache["type"] == "recent":
        title = f"最近 {cache['limit']} 条消息"
    else:
        title = f"@{config.TARGET_CHANNEL} 今日消息"
    
    text = channel.format_messages_page(messages, page, total_pages, title)
    keyboard = _build_page_keyboard(page, total_pages)
    
    await query.edit_message_text(lc7c(text), parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通文本消息"""
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    
    # 检查是否在对话模式
    if not settings["chat_mode"]:
        return  # 不在对话模式，忽略消息
    
    user_message = update.message.text
    user_name = update.effective_user.first_name or "用户"
    
    # 记录收到的消息
    logger.info(f"[收到] {user_name}: {user_message[:50]}{'...' if len(user_message) > 50 else ''}")
    
    # 发送"正在输入"状态
    await update.message.chat.send_action("typing")
    
    try:
        # 获取/初始化对话历史
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        history = user_conversations[user_id]
        history.append({"role": "user", "content": user_message})
        
        # 限制历史长度
        if len(history) > MAX_HISTORY * 2:
            history = history[-MAX_HISTORY * 2:]
            user_conversations[user_id] = history
        
        # 调用 AI
        response = chat.chat(history, settings["model"])
        
        # 记录返回的消息
        logger.info(f"[回复] Bot: {response[:50]}{'...' if len(response) > 50 else ''}")
        
        # 添加到历史
        history.append({"role": "assistant", "content": response})
        
        # 发送回复
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(lc7c(response[i:i+4000]))
        else:
            await update.message.reply_text(lc7c(response))
            
    except Exception as e:
        logger.error(f"AI 对话出错: {e}")
        error_msg = str(e)
        if "503" in error_msg or "unhealthy" in error_msg.lower():
            await update.message.reply_text(lc7c("❌ AI 服务不可用。请确保 Antigravity Manager 正在运行。"))
        else:
            await update.message.reply_text(lc7c(f"❌ 对话出错: {error_msg[:100]}"))


# ===== 定时任务 =====

async def scheduled_weather_push(context: ContextTypes.DEFAULT_TYPE):
    """定时推送天气（每日 8:00）"""
    logger.info("执行每日天气推送...")
    
    users = database.get_subscribed_users()
    for user_id in users:
        try:
            settings = database.get_user_settings(user_id)
            report = await weather.get_weather_report(settings["city"])
            await context.bot.send_message(chat_id=user_id, text=lc7c(report), parse_mode='Markdown')
        except Exception as e:
            logger.error(f"推送天气给用户 {user_id} 失败: {e}")


async def scheduled_channel_summary(context: ContextTypes.DEFAULT_TYPE):
    """定时推送频道汇总（每日 20:00）"""
    logger.info("执行每日频道汇总...")
    
    # 检查 Telethon 是否可用
    if not channel.telethon_client:
        logger.warning("Telethon 未初始化，跳过频道汇总")
        return
    
    try:
        summary = await channel.get_channel_summary()
        
        users = database.get_subscribed_users()
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=lc7c(summary), parse_mode='Markdown')
            except Exception as e:
                logger.error(f"推送汇总给用户 {user_id} 失败: {e}")
    except Exception as e:
        logger.error(f"获取频道汇总失败: {e}")


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
    chat.init_openai_client()
    logger.info("AI 客户端已初始化")


async def post_shutdown(application: Application):
    """应用关闭时的回调"""
    if channel.telethon_client:
        await channel.telethon_client.disconnect()
        logger.info("Telethon 客户端已断开")


def main():
    """主函数"""
    print("🤖 正在启动多功能 Bot...")
    
    # 初始化数据库
    database.init_db()
    
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
    
    # 添加图片消息处理器（用于 /image 搜图）
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # 添加回调查询处理器（翻页按钮）
    application.add_handler(CallbackQueryHandler(news_callback, pattern="^news_"))
    
    # 添加消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 添加错误处理器
    async def error_handler(update, context):
        logger.error(f"Bot 错误: {context.error}")
    application.add_error_handler(error_handler)
    
    # 添加定时任务（使用 UTC+8 时区）
    job_queue = application.job_queue
    # 每日 8:00 推送天气 (UTC+8)
    job_queue.run_daily(scheduled_weather_push, time=dt_time(hour=8, minute=0, tzinfo=CHINA_TZ))
    # 每日 20:00 推送天气 (UTC+8)
    job_queue.run_daily(scheduled_weather_push, time=dt_time(hour=20, minute=0, tzinfo=CHINA_TZ))
    # 每日 20:00 推送频道汇总 (UTC+8)
    job_queue.run_daily(scheduled_channel_summary, time=dt_time(hour=20, minute=0, tzinfo=CHINA_TZ))
    
    print("✅ Bot 已启动！")
    print("📌 功能: 天气预报 | 频道汇总 | AI 对话")
    print("⏰ 定时任务: 8:00/20:00 天气 | 20:00 频道汇总")
    print("按 Ctrl+C 停止")
    
    # 启动
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
