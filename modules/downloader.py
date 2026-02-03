"""
媒体下载器模块 - 使用 yt-dlp 下载视频
支持 YouTube、Bilibili、Twitter 等
"""
import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

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


def is_supported_url(url: str) -> bool:
    """检查 URL 是否支持下载"""
    return get_site_name(url) is not None


async def get_video_info(url: str) -> dict | None:
    """获取视频信息（不下载）"""
    try:
        cmd = [
            "yt-dlp",
            "--no-download",
            "--print", "%(title)s",
            "--print", "%(duration)s", 
            "--print", "%(filesize_approx)s",
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        
        if process.returncode == 0:
            lines = stdout.decode().strip().split('\n')
            if len(lines) >= 3:
                title = lines[0][:100]  # 限制标题长度
                duration = int(lines[1]) if lines[1].isdigit() else 0
                filesize = int(lines[2]) if lines[2].isdigit() else 0
                
                return {
                    "title": title,
                    "duration": duration,
                    "duration_str": f"{duration // 60}:{duration % 60:02d}" if duration else "未知",
                    "filesize": filesize,
                    "filesize_str": f"{filesize / 1024 / 1024:.1f}MB" if filesize else "未知",
                }
        else:
            logger.error(f"获取视频信息失败: {stderr.decode()[:200]}")
            
    except asyncio.TimeoutError:
        logger.error("获取视频信息超时")
    except FileNotFoundError:
        logger.error("yt-dlp 未安装")
    except Exception as e:
        logger.error(f"获取视频信息出错: {e}")
    
    return None


async def download_video(url: str, max_size_mb: int = 50) -> tuple[bool, str, str | None]:
    """
    下载视频
    返回: (成功与否, 消息/错误, 文件路径)
    """
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(title).50s.%(ext)s")
    
    try:
        # yt-dlp 命令
        cmd = [
            "yt-dlp",
            "-f", f"best[filesize<{max_size_mb}M]/bestvideo[filesize<{max_size_mb}M]+bestaudio/best",
            "-o", output_template,
            "--no-playlist",
            "--max-filesize", f"{max_size_mb}M",
            "--socket-timeout", "30",
            url
        ]
        
        logger.info(f"[下载] 开始下载: {url}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 等待完成，超时 5 分钟
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
        
        if process.returncode == 0:
            # 查找下载的文件
            files = list(Path(temp_dir).glob("*"))
            if files:
                video_file = files[0]
                file_size = video_file.stat().st_size / 1024 / 1024
                
                if file_size > max_size_mb:
                    return False, f"❌ 文件太大 ({file_size:.1f}MB)，超过 {max_size_mb}MB 限制", None
                
                logger.info(f"[下载] 成功: {video_file.name} ({file_size:.1f}MB)")
                return True, f"✅ 下载成功 ({file_size:.1f}MB)", str(video_file)
        
        error = stderr.decode()[:200]
        logger.error(f"[下载] 失败: {error}")
        
        if "Video unavailable" in error:
            return False, "❌ 视频不可用或已被删除", None
        elif "Private video" in error:
            return False, "❌ 这是私密视频，无法下载", None
        elif "Sign in" in error:
            return False, "❌ 需要登录才能下载", None
        else:
            return False, f"❌ 下载失败: {error[:100]}", None
            
    except asyncio.TimeoutError:
        return False, "❌ 下载超时（超过5分钟）", None
    except FileNotFoundError:
        return False, "❌ yt-dlp 未安装\n\n请运行: `pip install yt-dlp`", None
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
