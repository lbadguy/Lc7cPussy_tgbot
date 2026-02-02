"""
频道消息汇总模块 - 使用 Telethon 读取公开频道
"""
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.types import Message

import config

logger = logging.getLogger(__name__)

# Telethon 客户端（在主程序中初始化）
telethon_client: TelegramClient = None


def init_telethon_client():
    """初始化 Telethon 客户端"""
    global telethon_client
    
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        logger.warning("Telegram API ID/Hash 未配置，频道汇总功能不可用")
        return None
    
    try:
        api_id = int(config.TELEGRAM_API_ID)
    except (ValueError, TypeError):
        logger.error("TELEGRAM_API_ID 必须是数字")
        return None
    
    telethon_client = TelegramClient(
        'bot_session',  # session 文件名
        api_id,
        config.TELEGRAM_API_HASH
    )
    return telethon_client


async def get_today_messages(channel_username: str = None) -> list[dict]:
    """获取频道今日消息"""
    if not telethon_client:
        logger.error("Telethon 客户端未初始化")
        return []
    
    channel = channel_username or config.TARGET_CHANNEL
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    messages = []
    try:
        async for message in telethon_client.iter_messages(channel, limit=100):
            if not isinstance(message, Message) or not message.text:
                continue
            
            # 检查是否是今日消息
            msg_date = message.date.replace(tzinfo=None)
            if msg_date < today_start:
                break
            
            # 提取标题（取第一行或前80字符）
            text = message.text.strip()
            title = text.split('\n')[0][:80]
            if len(title) < len(text.split('\n')[0]):
                title += "..."
            
            messages.append({
                "id": message.id,
                "title": title,
                "date": msg_date.strftime("%H:%M"),
                "url": f"https://t.me/{channel}/{message.id}"
            })
    
    except Exception as e:
        logger.error(f"获取频道消息失败: {e}")
    
    return messages


def format_summary_message(messages: list[dict]) -> str:
    """格式化消息汇总"""
    if not messages:
        return "📰 今日该频道暂无新消息"
    
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"📰 **{config.TARGET_CHANNEL} 今日消息汇总** ({today})\n"]
    lines.append(f"共 {len(messages)} 条消息:\n")
    
    for i, msg in enumerate(messages[:20], 1):  # 最多显示20条
        lines.append(f"{i}. [{msg['date']}] {msg['title']}")
    
    if len(messages) > 20:
        lines.append(f"\n... 还有 {len(messages) - 20} 条消息")
    
    return "\n".join(lines)


async def get_channel_summary() -> str:
    """获取频道今日消息汇总"""
    messages = await get_today_messages()
    return format_summary_message(messages)
