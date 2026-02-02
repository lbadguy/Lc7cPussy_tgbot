"""
天气功能模块 - 使用和风天气 API
返回全面的天气信息
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
    """获取全面的天气数据"""
    result = {"now": None, "daily": None, "indices": None, "air": None}
    
    try:
        async with aiohttp.ClientSession() as session:
            params = {"location": location_id, "key": config.QWEATHER_API_KEY}
            
            # 实时天气
            now_url = f"{config.QWEATHER_BASE_URL}/weather/now"
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
            
            # 生活指数（穿衣、紫外线、运动等）
            indices_url = f"{config.QWEATHER_BASE_URL}/indices/1d"
            indices_params = {**params, "type": "1,2,3,5,9"}  # 运动、洗车、穿衣、紫外线、感冒
            async with session.get(indices_url, params=indices_params, timeout=10) as resp:
                data = await resp.json()
                if data.get("code") == "200":
                    result["indices"] = data.get("daily", [])
            
            # 空气质量（免费版可能不可用）
            try:
                air_url = f"{config.QWEATHER_BASE_URL}/air/now"
                async with session.get(air_url, params=params, timeout=5) as resp:
                    data = await resp.json()
                    if data.get("code") == "200":
                        result["air"] = data.get("now")
            except:
                pass  # 免费版可能没有空气质量接口
        
        return result
    except Exception as e:
        logger.error(f"获取天气失败: {e}")
        return None


def format_weather_message(city_name: str, weather_data: dict, detailed: bool = False) -> str:
    """格式化天气消息"""
    now = weather_data.get("now", {})
    daily = weather_data.get("daily", [])
    indices = weather_data.get("indices", [])
    air = weather_data.get("air")
    
    lines = [f"🌤 **{city_name} 天气预报**"]
    lines.append(f"🕐 更新时间: {datetime.now().strftime('%H:%M')}\n")
    
    # ===== 实时天气 =====
    if now:
        lines.append("━━━━ **实时天气** ━━━━")
        lines.append(f"🌡 **{now.get('text', '未知')}  {now.get('temp', '--')}°C**")
        lines.append(f"├ 体感温度: {now.get('feelsLike', '--')}°C")
        lines.append(f"├ 相对湿度: {now.get('humidity', '--')}%")
        lines.append(f"├ 风向风力: {now.get('windDir', '--')} {now.get('windScale', '--')}级")
        lines.append(f"├ 风速: {now.get('windSpeed', '--')} km/h")
        lines.append(f"├ 能见度: {now.get('vis', '--')} km")
        lines.append(f"├ 大气压: {now.get('pressure', '--')} hPa")
        if now.get('precip') and now.get('precip') != '0.0':
            lines.append(f"├ 降水量: {now.get('precip')} mm")
        lines.append(f"└ 云量: {now.get('cloud', '--')}%\n")
    
    # ===== 空气质量 =====
    if air:
        aqi = air.get('aqi', '--')
        category = air.get('category', '未知')
        lines.append(f"🌬 **空气质量**: AQI {aqi} ({category})")
        lines.append(f"├ PM2.5: {air.get('pm2p5', '--')} | PM10: {air.get('pm10', '--')}")
        lines.append(f"└ NO₂: {air.get('no2', '--')} | SO₂: {air.get('so2', '--')}\n")
    
    # ===== 今明预报 =====
    lines.append("━━━━ **今明预报** ━━━━")
    for i, day in enumerate(daily[:3]):
        if i == 0:
            date_str = "📅 今日"
        elif i == 1:
            date_str = "📅 明日"
        else:
            date_str = f"📅 后天"
        
        lines.append(f"{date_str} ({day.get('fxDate', '')})")
        lines.append(f"├ 天气: {day.get('textDay', '--')} → {day.get('textNight', '--')}")
        lines.append(f"├ 温度: {day.get('tempMin', '--')}°C ~ {day.get('tempMax', '--')}°C")
        lines.append(f"├ 风向: {day.get('windDirDay', '--')} {day.get('windScaleDay', '--')}级")
        lines.append(f"├ 湿度: {day.get('humidity', '--')}% | 紫外线: {day.get('uvIndex', '--')}")
        lines.append(f"├ 🌅 日出: {day.get('sunrise', '--')} | 🌇 日落: {day.get('sunset', '--')}")
        if day.get('precip') and day.get('precip') != '0.0':
            lines.append(f"├ 降水量: {day.get('precip', '--')} mm")
        lines.append("")
    
    # ===== 生活指数 =====
    if indices:
        lines.append("━━━━ **生活指数** ━━━━")
        for idx in indices:
            name = idx.get('name', '')
            category = idx.get('category', '')
            emoji = _get_index_emoji(name)
            lines.append(f"{emoji} {name}: {category}")
    
    return "\n".join(lines)


def _get_index_emoji(name: str) -> str:
    """获取指数对应的表情"""
    emoji_map = {
        "运动": "🏃",
        "洗车": "🚗",
        "穿衣": "👔",
        "紫外线": "☀️",
        "感冒": "🤧",
        "旅游": "✈️",
        "钓鱼": "🎣",
    }
    return emoji_map.get(name, "📊")


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
