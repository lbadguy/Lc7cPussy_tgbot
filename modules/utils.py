"""
工具函数模块
"""
import re
from datetime import datetime, timedelta, timezone

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))

# Bot 标识前缀
BOT_PREFIX = "[ LC7c ]\n\n"


def lc7c(text: str) -> str:
    """在消息前添加 Bot 标识前缀"""
    return BOT_PREFIX + text


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


def get_next_push_time(hour: int, minute: int = 0) -> str:
    """计算距离下次推送的时间"""
    now = datetime.now(CHINA_TZ)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if now >= target:
        target += timedelta(days=1)
    
    diff = target - now
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    return f"{minutes}分钟"
