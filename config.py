"""
配置管理模块
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 和风天气
QWEATHER_API_KEY = os.getenv("QWEATHER_API_KEY")
QWEATHER_BASE_URL = "https://devapi.qweather.com/v7"
QWEATHER_GEO_URL = "https://geoapi.qweather.com/v2"

# Telegram API (Telethon)
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

# Antigravity Manager
ANTIGRAVITY_API_KEY = os.getenv("ANTIGRAVITY_API_KEY", "sk-antigravity")
ANTIGRAVITY_BASE_URL = os.getenv("ANTIGRAVITY_BASE_URL", "http://127.0.0.1:8045/v1")

# 默认设置
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "佛山顺德")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-3-flash")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "zaihuapd")

# 支持的新闻频道列表
NEWS_CHANNELS = [
    {"name": "在华PD", "username": "zaihuapd", "has_title": True},
    {"name": "竹新社", "username": "tnews365", "has_title": False},
]

# 支持的模型列表
AVAILABLE_MODELS = [
    "gemini-3-flash",
    "gemini-3-pro-high",
    "gemini-3-pro-low",
    "gemini-3-pro-image",
    "gemini-2.5-flash",
    "gemini-2.5-flash-thinking",
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-thinking",
    "claude-opus-4-5-thinking",
]
