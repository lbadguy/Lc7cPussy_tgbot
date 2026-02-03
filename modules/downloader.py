"""
媒体下载器模块 - 使用 yt-dlp Python API
支持 YouTube、Bilibili、Twitter 等
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# 检查 yt-dlp 是否可用
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp 未安装，视频下载功能不可用")

# 支持的网站列表
SUPPORTED_SITES = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube", 
    "bilibili.com": "Bilibili",
    "b23.tv": "Bilibili",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "tiktok.com": "TikTok",
    "douyin.com": "抖音",
    "instagram.com": "Instagram",
    "weibo.com": "微博",
}


def get_site_name(url: str) -> str | None:
    """识别 URL 所属网站"""
    for domain, name in SUPPORTED_SITES.items():
        if domain in url:
            return name
    return None


def is_bilibili(url: str) -> bool:
    """检查是否是 B站链接"""
    return "bilibili.com" in url or "b23.tv" in url


def is_supported_url(url: str) -> bool:
    """检查 URL 是否支持下载"""
    return get_site_name(url) is not None


async def download_video(url: str, max_size_mb: int = 50) -> tuple[bool, str, str | None]:
    """
    下载视频（使用 Python API）
    返回: (成功与否, 消息/错误, 文件路径)
    """
    if not YT_DLP_AVAILABLE:
        return False, "❌ yt-dlp 未安装\n\n请运行: `pip install yt-dlp`", None
    
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(title).50s.%(ext)s")
    
    # 基础配置
    ydl_opts = {
        'outtmpl': output_template,
        'noplaylist': True,
        'socket_timeout': 30,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'merge_output_format': 'mp4',
        'geo_bypass': True,
        # 重要：忽略错误，尝试下载可用的格式
        'ignoreerrors': False,
    }
    
    # 根据网站选择不同的格式策略
    if is_bilibili(url):
        # B站特殊处理：
        # 1. 不登录只能下载 360p/480p
        # 2. 使用 format_sort 优先选择可用的格式
        ydl_opts['format'] = 'bv*+ba/b'  # 最佳视频+最佳音频，或最佳单一格式
        ydl_opts['format_sort'] = ['res:720', 'ext:mp4:m4a']  # 限制最高720p
        logger.info("[下载] 检测到 B站链接，使用兼容格式")
    else:
        # 其他网站：最高画质
        ydl_opts['format'] = 'bestvideo*+bestaudio*/best'
    
    try:
        logger.info(f"[下载] 开始下载: {url}")
        
        # 在线程池中运行（避免阻塞）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _download_sync, url, ydl_opts, temp_dir, max_size_mb)
        return result
        
    except Exception as e:
        logger.error(f"[下载] 出错: {e}")
        return False, f"❌ 下载出错: {str(e)[:100]}", None


def _download_sync(url: str, ydl_opts: dict, temp_dir: str, max_size_mb: int) -> tuple[bool, str, str | None]:
    """同步下载函数（在线程池中运行）"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 下载视频
            ydl.download([url])
        
        # 查找下载的文件
        files = list(Path(temp_dir).glob("*"))
        if files:
            video_file = files[0]
            file_size = video_file.stat().st_size / 1024 / 1024
            
            if file_size > max_size_mb:
                # 文件太大，尝试删除并返回错误
                video_file.unlink()
                return False, f"❌ 文件太大 ({file_size:.1f}MB)，超过 {max_size_mb}MB 限制\n\n_Telegram 限制最大 50MB_", None
            
            logger.info(f"[下载] 成功: {video_file.name} ({file_size:.1f}MB)")
            return True, f"✅ 下载成功 ({file_size:.1f}MB)", str(video_file)
        
        return False, "❌ 下载完成但找不到文件", None
        
    except yt_dlp.utils.DownloadError as e:
        error = str(e)
        logger.error(f"[下载] 失败: {error[:200]}")
        
        # 针对不同错误给出友好提示
        if "Video unavailable" in error:
            return False, "❌ 视频不可用或已被删除", None
        elif "Private video" in error:
            return False, "❌ 这是私密视频，无法下载", None
        elif "Sign in" in error or "login" in error.lower():
            return False, "❌ 需要登录才能下载此视频", None
        elif "HTTP Error 403" in error:
            return False, "❌ 访问被拒绝（403）", None
        elif "Requested format is not available" in error:
            # B站可能需要登录才能获取高清
            if is_bilibili(ydl_opts.get('original_url', '')):
                return False, "❌ B站需要登录才能下载\n\n_高清格式需要登录账号_", None
            return False, "❌ 请求的格式不可用", None
        elif "Unable to extract" in error:
            return False, "❌ 无法解析视频信息\n\n_链接可能已失效_", None
        else:
            return False, f"❌ 下载失败: {error[:80]}", None
            
    except Exception as e:
        logger.error(f"[下载] 出错: {e}")
        return False, f"❌ 下载出错: {str(e)[:100]}", None


def cleanup_file(file_path: str):
    """清理下载的临时文件"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            # 尝试删除临时目录
            parent = os.path.dirname(file_path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
    except Exception as e:
        logger.warning(f"清理文件失败: {e}")
