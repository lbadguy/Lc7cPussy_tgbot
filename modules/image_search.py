"""
图片搜索模块 - 以图搜图功能
支持 Google Lens、Yandex、SauceNAO、TinEye
"""
import aiohttp
import logging
import base64
from io import BytesIO

logger = logging.getLogger(__name__)


async def upload_to_telegraph(image_bytes: bytes) -> str | None:
    """上传图片到 Telegraph，返回图片 URL"""
    try:
        form = aiohttp.FormData()
        form.add_field('file', image_bytes, filename='image.jpg', content_type='image/jpeg')
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://telegra.ph/upload', data=form, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0 and 'src' in data[0]:
                        return 'https://telegra.ph' + data[0]['src']
    except Exception as e:
        logger.error(f"上传图片到 Telegraph 失败: {e}")
    return None


async def upload_to_catbox(image_bytes: bytes) -> str | None:
    """上传图片到 Catbox.moe，返回图片 URL（备用方案）"""
    try:
        form = aiohttp.FormData()
        form.add_field('reqtype', 'fileupload')
        form.add_field('fileToUpload', image_bytes, filename='image.jpg', content_type='image/jpeg')
        
        async with aiohttp.ClientSession() as session:
            async with session.post('https://catbox.moe/user/api.php', data=form, timeout=30) as resp:
                if resp.status == 200:
                    url = await resp.text()
                    if url.startswith('https://'):
                        return url.strip()
    except Exception as e:
        logger.error(f"上传图片到 Catbox 失败: {e}")
    return None


def generate_search_links(image_url: str) -> dict:
    """生成各搜索引擎的搜图链接"""
    from urllib.parse import quote
    
    encoded_url = quote(image_url, safe='')
    
    return {
        "google": f"https://lens.google.com/uploadbyurl?url={encoded_url}",
        "yandex": f"https://yandex.com/images/search?rpt=imageview&url={encoded_url}",
        "bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:{encoded_url}",
        "tineye": f"https://tineye.com/search?url={encoded_url}",
        "saucenao": f"https://saucenao.com/search.php?url={encoded_url}",
        "iqdb": f"https://iqdb.org/?url={encoded_url}",
    }


def format_search_result(image_url: str) -> str:
    """格式化搜图结果消息"""
    links = generate_search_links(image_url)
    
    lines = [
        "🔍 **以图搜图**\n",
        "点击下方链接搜索相似图片：\n",
        f"🌐 [Google Lens]({links['google']})",
        f"🔵 [Yandex Images]({links['yandex']})",
        f"🟦 [Bing Visual]({links['bing']})",
        f"👁 [TinEye]({links['tineye']})",
        "",
        "**二次元/动漫专用：**",
        f"🎨 [SauceNAO]({links['saucenao']})",
        f"📚 [IQDB]({links['iqdb']})",
        "",
        f"_图片已上传至: [点击查看]({image_url})_"
    ]
    
    return "\n".join(lines)


async def search_image(image_bytes: bytes) -> tuple[bool, str]:
    """
    主函数：上传图片并生成搜索链接
    返回: (成功与否, 结果消息)
    """
    # 尝试上传到 Telegraph
    image_url = await upload_to_telegraph(image_bytes)
    
    # 如果失败，尝试 Catbox
    if not image_url:
        image_url = await upload_to_catbox(image_bytes)
    
    if not image_url:
        return False, "❌ 图片上传失败，请稍后重试"
    
    result = format_search_result(image_url)
    return True, result
