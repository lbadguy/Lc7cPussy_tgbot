"""
工具函数模块
"""
import re
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))

# Bot 标识前缀
BOT_PREFIX = "〔 LC7c 〕\n\n"


def lc7c(text: str) -> str:
    """在消息前添加 Bot 标识前缀"""
    return BOT_PREFIX + text


async def safe_reply(message, text, parse_mode='Markdown', **kwargs):
    """安全发送回复：Markdown 解析失败时自动降级为纯文本
    
    解决 'Can't parse entities' 错误
    """
    if parse_mode:
        try:
            return await message.reply_text(text, parse_mode=parse_mode, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if 'parse' in error_str or 'entities' in error_str or "can't find end" in error_str:
                logger.warning(f"Markdown 解析失败，降级为纯文本: {e}")
                return await message.reply_text(text, **kwargs)
            raise
    return await message.reply_text(text, **kwargs)


async def safe_edit(message, text, parse_mode='Markdown', **kwargs):
    """安全编辑消息：Markdown 解析失败时自动降级为纯文本
    
    支持 CallbackQuery（edit_message_text）和 Message（edit_text）
    解决 'Can't parse entities' 错误
    """
    # 判断是 CallbackQuery 还是 Message
    edit_fn = getattr(message, 'edit_message_text', None) or message.edit_text
    
    if parse_mode:
        try:
            return await edit_fn(text, parse_mode=parse_mode, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if 'parse' in error_str or 'entities' in error_str or "can't find end" in error_str:
                logger.warning(f"Markdown 解析失败，降级为纯文本: {e}")
                return await edit_fn(text, **kwargs)
            raise
    return await edit_fn(text, **kwargs)


def clean_ai_response(text: str) -> str:
    """
    清理 AI 回复中的 Markdown 符号，让消息更易读
    """
    # 移除标题符号 (# ## ### 等)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # 移除粗体标记 **text** -> text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    
    # 移除斜体标记 *text* 或 _text_ -> text
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # 移除代码块标记 ```code``` -> code
    text = re.sub(r'```[\w]*\n?', '', text)
    
    # 移除行内代码 `code` -> code
    text = re.sub(r'`(.+?)`', r'\1', text)
    
    # 列表符号美化 - item -> • item
    text = re.sub(r'^[\-\*]\s+', '• ', text, flags=re.MULTILINE)
    
    # 移除链接格式 [text](url) -> text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    
    # 移除多余的空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
