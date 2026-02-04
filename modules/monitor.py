"""
手机状态监控模块 (Termux 专用)
功能：电量监控、网络监控、流量统计
"""
import asyncio
import logging
import subprocess
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# 检测是否在 Termux 环境
IS_TERMUX = os.path.exists("/data/data/com.termux")

# 流量统计起始值（脚本启动时记录）
_start_time = None
_start_rx_bytes = 0
_start_tx_bytes = 0

# 上次网络状态
_last_network_ok = True


def init_monitor():
    """初始化监控（记录启动时的流量）"""
    global _start_time, _start_rx_bytes, _start_tx_bytes
    _start_time = datetime.now()
    rx, tx = _get_network_bytes()
    _start_rx_bytes = rx
    _start_tx_bytes = tx
    logger.info(f"[监控] 初始化完成，起始流量: RX={_format_bytes(rx)}, TX={_format_bytes(tx)}")


def _run_termux_cmd(cmd: str) -> dict | None:
    """运行 Termux API 命令并返回 JSON"""
    if not IS_TERMUX:
        return None
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"[监控] 命令执行失败 {cmd}: {e}")
    return None


def get_battery_info() -> dict:
    """获取电池信息"""
    if not IS_TERMUX:
        return {"available": False, "message": "非 Termux 环境"}
    
    data = _run_termux_cmd("termux-battery-status")
    if data:
        return {
            "available": True,
            "percentage": data.get("percentage", -1),
            "status": data.get("status", "unknown"),
            "plugged": data.get("plugged", "unknown"),
            "temperature": data.get("temperature", 0),
        }
    return {"available": False, "message": "无法获取电池信息"}


def check_network() -> bool:
    """检查网络连接（ping 测试）"""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def _get_network_bytes() -> tuple[int, int]:
    """获取网络流量（字节）"""
    rx_bytes = 0
    tx_bytes = 0
    
    try:
        with open("/proc/net/dev", "r") as f:
            for line in f:
                if ":" in line and not line.strip().startswith("lo:"):
                    parts = line.split()
                    if len(parts) >= 10:
                        # 格式: interface: rx_bytes ... tx_bytes ...
                        rx_bytes += int(parts[1])
                        tx_bytes += int(parts[9])
    except Exception as e:
        logger.warning(f"[监控] 读取流量失败: {e}")
    
    return rx_bytes, tx_bytes


def _format_bytes(bytes_val: int) -> str:
    """格式化字节数"""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.2f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / 1024 / 1024:.2f} MB"
    else:
        return f"{bytes_val / 1024 / 1024 / 1024:.2f} GB"


def get_network_stats() -> dict:
    """获取网络流量统计"""
    global _start_time, _start_rx_bytes, _start_tx_bytes
    
    if _start_time is None:
        init_monitor()
    
    current_rx, current_tx = _get_network_bytes()
    
    # 计算增量
    rx_delta = current_rx - _start_rx_bytes
    tx_delta = current_tx - _start_tx_bytes
    
    # 计算运行时间
    runtime = datetime.now() - _start_time
    hours = runtime.total_seconds() / 3600
    
    return {
        "download": _format_bytes(rx_delta),
        "upload": _format_bytes(tx_delta),
        "total": _format_bytes(rx_delta + tx_delta),
        "runtime_hours": round(hours, 2),
        "runtime_str": str(runtime).split('.')[0],  # 去掉微秒
    }


def get_status_text() -> str:
    """获取完整状态文本"""
    lines = ["📱 **手机状态**\n"]
    
    # 电池信息
    battery = get_battery_info()
    if battery["available"]:
        emoji = "🔋" if battery["percentage"] > 20 else "🪫"
        plug = "⚡" if battery["plugged"] != "UNPLUGGED" else ""
        lines.append(f"{emoji} 电量: {battery['percentage']}% {plug}")
        lines.append(f"   状态: {battery['status']}")
        lines.append(f"   温度: {battery['temperature']}°C")
    else:
        lines.append(f"🔋 电量: {battery['message']}")
    
    lines.append("")
    
    # 网络状态
    network_ok = check_network()
    net_emoji = "🌐" if network_ok else "❌"
    net_status = "正常" if network_ok else "断开"
    lines.append(f"{net_emoji} 网络: {net_status}")
    
    # 流量统计
    stats = get_network_stats()
    lines.append(f"📊 流量统计 (运行 {stats['runtime_str']})")
    lines.append(f"   ↓ 下载: {stats['download']}")
    lines.append(f"   ↑ 上传: {stats['upload']}")
    lines.append(f"   总计: {stats['total']}")
    
    return "\n".join(lines)


def get_net_text() -> str:
    """获取流量统计文本"""
    stats = get_network_stats()
    
    lines = [
        "📊 **流量统计**\n",
        f"⏱ 运行时间: {stats['runtime_str']}",
        f"↓ 下载: {stats['download']}",
        f"↑ 上传: {stats['upload']}",
        f"📦 总计: {stats['total']}",
    ]
    
    return "\n".join(lines)


async def monitor_loop(send_alert):
    """
    监控循环（每 10 分钟检查一次）
    
    Args:
        send_alert: 发送警报的回调函数 async def(message: str)
    """
    global _last_network_ok
    
    if not IS_TERMUX:
        logger.info("[监控] 非 Termux 环境，监控功能禁用")
        return
    
    init_monitor()
    logger.info("[监控] 开始监控循环（每 10 分钟）")
    
    while True:
        try:
            # 检查电量
            battery = get_battery_info()
            if battery["available"]:
                if battery["percentage"] <= 15 and battery["plugged"] == "UNPLUGGED":
                    await send_alert(
                        f"🪫 **电量警告**\n\n"
                        f"手机电量仅剩 {battery['percentage']}%！\n"
                        f"请尽快充电，否则 Bot 可能会离线。"
                    )
            
            # 检查网络
            network_ok = check_network()
            if not network_ok and _last_network_ok:
                # 网络刚断开
                await send_alert(
                    "❌ **网络警告**\n\n"
                    "手机网络连接中断！\n"
                    "请检查网络状态。"
                )
            elif network_ok and not _last_network_ok:
                # 网络恢复
                await send_alert(
                    "✅ **网络恢复**\n\n"
                    "手机网络已恢复正常。"
                )
            _last_network_ok = network_ok
            
        except Exception as e:
            logger.error(f"[监控] 检查出错: {e}")
        
        # 等待 10 分钟
        await asyncio.sleep(600)
