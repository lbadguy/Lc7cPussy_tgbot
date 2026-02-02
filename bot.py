"""
多功能 Telegram Bot 主程序

功能：
1. 天气预报 - 每日 8:00 推送，/weather 指令
2. 频道汇总 - 每日 20:00 推送 @zaihuapd 消息汇总
3. AI 对话 - /chat 指令进入对话模式（需要反代服务）
"""
import asyncio
import logging
from datetime import time as dt_time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import config
from modules import weather, channel, chat, database

# 配置日志
# 文件日志：记录所有信息
file_handler = logging.FileHandler('bot_debug.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 终端日志：只显示警告和错误
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# 应用配置
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# 用户对话历史（内存存储，限制长度）
user_conversations = {}
MAX_HISTORY = 10


# ===== 命令处理器 =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user_id = update.effective_user.id
    
    # 添加订阅
    database.add_subscription(user_id)
    
    welcome = """
👋 **欢迎使用多功能助手 Bot！**

📌 **功能列表**

🌤 **天气预报**
• `/weather` - 查看当前城市天气
• `/weather 城市名` - 设置新城市
• 每日 8:00 自动推送天气

📰 **频道消息汇总**
• 每日 20:00 推送 @zaihuapd 今日消息

🤖 **AI 对话**（需开启反代服务）
• `/chat` - 进入 AI 对话模式
• `/chat off` - 退出对话模式
• `/model` - 查看/切换模型
• `/test` - 测试 API 连接

已为您开启每日推送服务！🎉
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    help_text = """
📖 **命令帮助**

**天气相关**
• `/weather` - 查看天气
• `/weather 北京` - 切换城市

**AI 对话**
• `/chat` - 开启对话
• `/chat off` - 关闭对话
• `/model` - 查看模型
• `/model gemini-3-flash` - 切换模型
• `/test` - 测试连接

**其他**
• `/start` - 重新开始
• `/help` - 显示帮助
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


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
            await update.message.reply_text(report, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ 未找到城市: {new_city}")
    else:
        # 显示当前城市天气
        city = settings["city"]
        await update.message.reply_text(f"🔍 正在获取 {city} 的天气...")
        report = await weather.get_weather_report(city)
        await update.message.reply_text(report, parse_mode='Markdown')


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /chat 命令"""
    user_id = update.effective_user.id
    
    # 检查是否要关闭
    if context.args and context.args[0].lower() == "off":
        database.update_chat_mode(user_id, False)
        if user_id in user_conversations:
            del user_conversations[user_id]
        await update.message.reply_text("🔴 已退出 AI 对话模式")
        return
    
    # 开启对话模式
    database.update_chat_mode(user_id, True)
    user_conversations[user_id] = []
    
    settings = database.get_user_settings(user_id)
    await update.message.reply_text(
        f"🟢 已进入 AI 对话模式\n"
        f"当前模型: `{settings['model']}`\n\n"
        f"直接发送消息开始对话\n"
        f"使用 `/chat off` 退出",
        parse_mode='Markdown'
    )


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /model 命令"""
    user_id = update.effective_user.id
    
    if context.args:
        new_model = context.args[0]
        if chat.is_valid_model(new_model):
            database.update_user_model(user_id, new_model)
            await update.message.reply_text(f"✅ 模型已切换为: `{new_model}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"❌ 无效的模型名称: {new_model}\n\n" + chat.get_model_list(),
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(chat.get_model_list(), parse_mode='Markdown')


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /test 命令 - 测试 AI 连接"""
    await update.message.reply_text("🔄 正在测试 AI API 连接...")
    
    success, message = await chat.test_connection()
    await update.message.reply_text(message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通文本消息"""
    user_id = update.effective_user.id
    settings = database.get_user_settings(user_id)
    
    # 检查是否在对话模式
    if not settings["chat_mode"]:
        return  # 不在对话模式，忽略消息
    
    user_message = update.message.text
    
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
        
        # 添加到历史
        history.append({"role": "assistant", "content": response})
        
        # 发送回复
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await update.message.reply_text(response[i:i+4000])
        else:
            await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"AI 对话出错: {e}")
        error_msg = str(e)
        if "503" in error_msg or "unhealthy" in error_msg.lower():
            await update.message.reply_text("❌ AI 服务不可用。请确保 Antigravity Manager 正在运行。")
        else:
            await update.message.reply_text(f"❌ 对话出错: {error_msg[:100]}")


# ===== 定时任务 =====

async def scheduled_weather_push(context: ContextTypes.DEFAULT_TYPE):
    """定时推送天气（每日 8:00）"""
    logger.info("执行每日天气推送...")
    
    users = database.get_subscribed_users()
    for user_id in users:
        try:
            settings = database.get_user_settings(user_id)
            report = await weather.get_weather_report(settings["city"])
            await context.bot.send_message(chat_id=user_id, text=report, parse_mode='Markdown')
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
                await context.bot.send_message(chat_id=user_id, text=summary, parse_mode='Markdown')
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
    
    # 添加消息处理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 添加错误处理器
    async def error_handler(update, context):
        logger.error(f"Bot 错误: {context.error}")
    application.add_error_handler(error_handler)
    
    # 添加定时任务
    job_queue = application.job_queue
    # 每日 8:00 推送天气 (UTC+8)
    job_queue.run_daily(scheduled_weather_push, time=dt_time(hour=8, minute=0))
    # 每日 20:00 推送频道汇总 (UTC+8)
    job_queue.run_daily(scheduled_channel_summary, time=dt_time(hour=20, minute=0))
    
    print("✅ Bot 已启动！")
    print("📌 功能: 天气预报 | 频道汇总 | AI 对话")
    print("⏰ 定时任务: 8:00 天气 | 20:00 频道汇总")
    print("按 Ctrl+C 停止")
    
    # 启动
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
