"""
频道消息汇总模块 - 使用 Telethon 读取公开频道
支持翻页、搜索等功能
"""
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.types import Message

import config

logger = logging.getLogger(__name__)

# Telethon 客户端（在主程序中初始化）
telethon_client: TelegramClient = None

# 每页显示消息数
PAGE_SIZE = 10


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
        'bot_session',
        api_id,
        config.TELEGRAM_API_HASH
    )
    return telethon_client


async def get_messages(channel_username: str = None, limit: int = 50, today_only: bool = True) -> list[dict]:
    """获取频道消息"""
    if not telethon_client:
        logger.error("Telethon 客户端未初始化")
        return []
    
    channel = channel_username or config.TARGET_CHANNEL
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    messages = []
    try:
        async for message in telethon_client.iter_messages(channel, limit=limit):
            if not isinstance(message, Message) or not message.text:
                continue
            
            msg_date = message.date.replace(tzinfo=None)
            
            # 如果只要今日消息，检查日期
            if today_only and msg_date < today_start:
                break
            
            # 提取标题（取第一行或前60字符）
            text = message.text.strip()
            first_line = text.split('\n')[0]
            title = first_line[:60]
            if len(title) < len(first_line):
                title += "..."
            
            messages.append({
                "id": message.id,
                "title": title,
                "date": msg_date.strftime("%H:%M"),
                "full_date": msg_date.strftime("%m-%d %H:%M"),
                "url": f"https://t.me/{channel}/{message.id}"
            })
    
    except Exception as e:
        logger.error(f"获取频道消息失败: {e}")
    
    return messages


async def search_messages(keyword: str, limit: int = 30) -> list[dict]:
    """搜索频道消息"""
    if not telethon_client:
        return []
    
    channel = config.TARGET_CHANNEL
    messages = []
    
    try:
        async for message in telethon_client.iter_messages(channel, limit=200, search=keyword):
            if not isinstance(message, Message) or not message.text:
                continue
            
            msg_date = message.date.replace(tzinfo=None)
            text = message.text.strip()
            first_line = text.split('\n')[0][:60]
            
            messages.append({
                "id": message.id,
                "title": first_line + ("..." if len(text.split('\n')[0]) > 60 else ""),
                "full_date": msg_date.strftime("%m-%d %H:%M"),
                "url": f"https://t.me/{channel}/{message.id}"
            })
            
            if len(messages) >= limit:
                break
    
    except Exception as e:
        logger.error(f"搜索频道消息失败: {e}")
    
    return messages


def format_messages_page(messages: list[dict], page: int = 1, total_pages: int = 1, title: str = "消息列表") -> str:
    """格式化消息页面"""
    if not messages:
        return "📭 没有找到消息"
    
    lines = [f"📰 **{title}**"]
    lines.append(f"📄 第 {page}/{total_pages} 页 | 共 {len(messages) if page == 1 else ''}条\n")
    
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_messages = messages[start:end]
    
    for i, msg in enumerate(page_messages, start + 1):
        # 使用链接格式
        date_str = msg.get('full_date', msg.get('date', ''))
        lines.append(f"**{i}.** `{date_str}`")
        lines.append(f"    [{msg['title']}]({msg['url']})\n")
    
    return "\n".join(lines)


def get_total_pages(messages: list[dict]) -> int:
    """计算总页数"""
    return max(1, (len(messages) + PAGE_SIZE - 1) // PAGE_SIZE)


async def get_channel_summary() -> str:
    """获取频道今日消息汇总（用于定时推送）"""
    messages = await get_messages(today_only=True)
    
    if not messages:
        return "📭 今日该频道暂无新消息"
    
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"📰 **@{config.TARGET_CHANNEL} 今日汇总**"]
    lines.append(f"📅 {today} | 共 {len(messages)} 条\n")
    
    for i, msg in enumerate(messages[:15], 1):
        lines.append(f"**{i}.** `{msg['date']}` [{msg['title']}]({msg['url']})")
    
    if len(messages) > 15:
        lines.append(f"\n... 还有 {len(messages) - 15} 条，发送 /news 查看全部")
    
    return "\n".join(lines)
