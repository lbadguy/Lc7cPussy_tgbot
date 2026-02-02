"""
天气功能模块 - 使用和风天气 API
"""
import aiohttp
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


async def search_city(city_name: str) -> dict | None:
    """搜索城市，返回城市信息"""
    url = f"{config.QWEATHER_GEO_URL}/city/lookup"
    params = {
        "location": city_name,
        "key": config.QWEATHER_API_KEY,
        "number": 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                if data.get("code") == "200" and data.get("location"):
                    return data["location"][0]
    except Exception as e:
        logger.error(f"搜索城市失败: {e}")
    return None


async def get_weather(location_id: str) -> dict | None:
    """获取当前天气和未来3天预报"""
    result = {"now": None, "daily": None}
    
    try:
        async with aiohttp.ClientSession() as session:
            # 实时天气
            now_url = f"{config.QWEATHER_BASE_URL}/weather/now"
            params = {"location": location_id, "key": config.QWEATHER_API_KEY}
            
            async with session.get(now_url, params=params, timeout=10) as resp:
                data = await resp.json()
                if data.get("code") == "200":
                    result["now"] = data.get("now")
            
            # 3天预报
            daily_url = f"{config.QWEATHER_BASE_URL}/weather/3d"
            async with session.get(daily_url, params=params, timeout=10) as resp:
                data = await resp.json()
                if data.get("code") == "200":
                    result["daily"] = data.get("daily", [])
        
        return result
    except Exception as e:
        logger.error(f"获取天气失败: {e}")
        return None


def format_weather_message(city_name: str, weather_data: dict) -> str:
    """格式化天气消息"""
    now = weather_data.get("now", {})
    daily = weather_data.get("daily", [])
    
    lines = [f"🌤 **{city_name} 天气预报**\n"]
    
    # 当前天气
    if now:
        lines.append(f"**现在**: {now.get('text', '未知')} {now.get('temp', '--')}°C")
        lines.append(f"体感温度: {now.get('feelsLike', '--')}°C | 湿度: {now.get('humidity', '--')}%")
        lines.append(f"风向: {now.get('windDir', '--')} {now.get('windScale', '--')}级\n")
    
    # 今日和明日预报
    for i, day in enumerate(daily[:2]):
        date_str = "今日" if i == 0 else "明日"
        lines.append(f"**{date_str}** ({day.get('fxDate', '')})")
        lines.append(f"  白天: {day.get('textDay', '--')} | 夜间: {day.get('textNight', '--')}")
        lines.append(f"  温度: {day.get('tempMin', '--')}°C ~ {day.get('tempMax', '--')}°C")
    
    return "\n".join(lines)


async def get_weather_report(city_name: str) -> str:
    """获取完整的天气报告"""
    # 搜索城市
    city_info = await search_city(city_name)
    if not city_info:
        return f"❌ 未找到城市: {city_name}"
    
    # 获取天气
    weather_data = await get_weather(city_info["id"])
    if not weather_data:
        return f"❌ 获取天气失败，请稍后重试"
    
    return format_weather_message(city_info["name"], weather_data)
