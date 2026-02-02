"""
数据库模块 - SQLite 持久化存储
"""
import os
import sqlite3
import logging

import config

logger = logging.getLogger(__name__)


def init_db():
    """初始化数据库"""
    # 确保 data 目录存在
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    # 用户设置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            city TEXT DEFAULT '佛山顺德',
            model TEXT DEFAULT 'gemini-3-flash',
            chat_mode INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 订阅用户表（用于定时推送）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            weather_enabled INTEGER DEFAULT 1,
            channel_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"数据库初始化完成: {config.DB_PATH}")


def get_user_settings(user_id: int) -> dict:
    """获取用户设置"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT city, model, chat_mode FROM user_settings WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"city": row[0], "model": row[1], "chat_mode": bool(row[2])}
    else:
        return {"city": config.DEFAULT_CITY, "model": config.DEFAULT_MODEL, "chat_mode": False}


def update_user_city(user_id: int, city: str):
    """更新用户城市"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO user_settings (user_id, city) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET city = ?, updated_at = CURRENT_TIMESTAMP
    ''', (user_id, city, city))
    
    conn.commit()
    conn.close()


def update_user_model(user_id: int, model: str):
    """更新用户模型"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO user_settings (user_id, model) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET model = ?, updated_at = CURRENT_TIMESTAMP
    ''', (user_id, model, model))
    
    conn.commit()
    conn.close()


def update_chat_mode(user_id: int, enabled: bool):
    """更新聊天模式"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO user_settings (user_id, chat_mode) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET chat_mode = ?, updated_at = CURRENT_TIMESTAMP
    ''', (user_id, int(enabled), int(enabled)))
    
    conn.commit()
    conn.close()


def add_subscription(user_id: int):
    """添加订阅"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO subscriptions (user_id) VALUES (?)
    ''', (user_id,))
    
    conn.commit()
    conn.close()


def get_subscribed_users() -> list[int]:
    """获取所有订阅用户"""
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM subscriptions WHERE weather_enabled = 1 OR channel_enabled = 1')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return users
