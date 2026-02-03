"""
图片搜索模块 - 以图搜图功能
支持 Google Lens、Yandex、SauceNAO、TinEye
"""
import aiohttp
import logging
import base64
import os
from urllib.parse import quote

logger = logging.getLogger(__name__)

# 获取代理设置（从环境变量）
PROXY = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or os.environ.get('HTTPS_PROXY')


async def upload_to_telegraph(image_bytes: bytes) -> str | None:
    """上传图片到 Telegraph，返回图片 URL"""
    try:
        form = aiohttp.FormData()
        form.add_field('file', image_bytes, filename='image.jpg', content_type='image/jpeg')
        
        connector = aiohttp.TCPConnector(ssl=False) if PROXY else None
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.post('https://telegra.ph/upload', data=form, proxy=PROXY) as resp:
                logger.info(f"[Telegraph] 响应状态: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0 and 'src' in data[0]:
                        url = 'https://telegra.ph' + data[0]['src']
                        logger.info(f"[Telegraph] 上传成功: {url}")
                        return url
                    else:
                        logger.warning(f"[Telegraph] 响应格式异常: {data}")
                else:
                    text = await resp.text()
                    logger.warning(f"[Telegraph] 上传失败: {resp.status} - {text[:100]}")
    except aiohttp.ClientConnectorError as e:
        logger.error(f"[Telegraph] 连接失败（可能需要代理）: {e}")
    except Exception as e:
        logger.error(f"[Telegraph] 上传失败: {type(e).__name__}: {e}")
    return None


async def upload_to_catbox(image_bytes: bytes) -> str | None:
    """上传图片到 Catbox.moe，返回图片 URL（备用方案）"""
    try:
        form = aiohttp.FormData()
        form.add_field('reqtype', 'fileupload')
        form.add_field('fileToUpload', image_bytes, filename='image.jpg', content_type='image/jpeg')
        
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post('https://catbox.moe/user/api.php', data=form, proxy=PROXY) as resp:
                logger.info(f"[Catbox] 响应状态: {resp.status}")
                if resp.status == 200:
                    url = await resp.text()
                    if url.startswith('https://'):
                        logger.info(f"[Catbox] 上传成功: {url.strip()}")
                        return url.strip()
                    else:
                        logger.warning(f"[Catbox] 响应异常: {url[:100]}")
    except aiohttp.ClientConnectorError as e:
        logger.error(f"[Catbox] 连接失败（可能需要代理）: {e}")
    except Exception as e:
        logger.error(f"[Catbox] 上传失败: {type(e).__name__}: {e}")
    return None


async def upload_to_imgbb(image_bytes: bytes) -> str | None:
    """上传到 ImgBB（免费图床，备用）"""
    try:
        # ImgBB 免费 API（无需 key 的公共端点）
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        form = aiohttp.FormData()
        form.add_field('image', b64)
        
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 使用免费的 freeimage.host
            async with session.post('https://freeimage.host/api/1/upload?key=6d207e02198a847aa98d0a2a901485a5', 
                                   data=form, proxy=PROXY) as resp:
                logger.info(f"[FreeImage] 响应状态: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('success') and data.get('image', {}).get('url'):
                        url = data['image']['url']
                        logger.info(f"[FreeImage] 上传成功: {url}")
                        return url
    except Exception as e:
        logger.error(f"[FreeImage] 上传失败: {type(e).__name__}: {e}")
    return None


def generate_search_links(image_url: str) -> dict:
    """生成各搜索引擎的搜图链接"""
    encoded_url = quote(image_url, safe='')
    
    return {
        "google": f"https://lens.google.com/uploadbyurl?url={encoded_url}",
        "google_old": f"https://www.google.com/searchbyimage?image_url={encoded_url}",
        "yandex": f"https://yandex.com/images/search?rpt=imageview&url={encoded_url}",
        "bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:{encoded_url}",
        "tineye": f"https://tineye.com/search?url={encoded_url}",
        "saucenao": f"https://saucenao.com/search.php?url={encoded_url}",
        "iqdb": f"https://iqdb.org/?url={encoded_url}",
        "ascii2d": f"https://ascii2d.net/search/url/{encoded_url}",
    }


def build_search_result(image_url: str) -> tuple[str, list]:
    """
    构建搜图结果（文本 + 按钮键盘）
    返回: (消息文本, 按钮行列表)
    """
    links = generate_search_links(image_url)
    
    # 消息文本（简洁版）
    text = (
        "🔍 **以图搜图**\n\n"
        "点击下方按钮搜索相似图片\n"
        "⏰ _链接有效期约 1 小时_"
    )
    
    # 按钮键盘布局（模仿你发的图片样式）
    keyboard = [
        # 第一行：Google
        [
            {"text": "Google Lens 🌐", "url": links["google"]},
            {"text": "Google 旧版", "url": links["google_old"]},
        ],
        # 第二行：Yandex
        [
            {"text": "Yandex 🔵", "url": links["yandex"]},
            {"text": "Bing 🟦", "url": links["bing"]},
        ],
        # 第三行：动漫搜图
        [
            {"text": "SauceNAO 🎨", "url": links["saucenao"]},
            {"text": "ascii2d", "url": links["ascii2d"]},
            {"text": "IQDB 📚", "url": links["iqdb"]},
        ],
        # 第四行：其他
        [
            {"text": "TinEye 👁", "url": links["tineye"]},
            {"text": "📷 查看图片", "url": image_url},
        ],
    ]
    
    return text, keyboard


# 保留旧函数兼容
def format_search_result(image_url: str) -> str:
    """格式化搜图结果消息（纯文本版，备用）"""
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
        "⏰ _链接有效期约 1 小时_"
    ]
    
    return "\n".join(lines)


async def search_image(image_bytes: bytes) -> tuple[bool, str]:
    """
    主函数：上传图片并生成搜索链接
    返回: (成功与否, 结果消息)
    """
    logger.info(f"[搜图] 开始上传图片，大小: {len(image_bytes)} bytes, 代理: {PROXY or '无'}")
    
    # 依次尝试多个图床
    image_url = await upload_to_telegraph(image_bytes)
    
    if not image_url:
        logger.info("[搜图] Telegraph 失败，尝试 Catbox...")
        image_url = await upload_to_catbox(image_bytes)
    
    if not image_url:
        logger.info("[搜图] Catbox 失败，尝试 FreeImage...")
        image_url = await upload_to_imgbb(image_bytes)
    
    if not image_url:
        logger.error("[搜图] 所有图床都失败了")
        return False, "❌ 图片上传失败\n\n可能原因：\n• 网络连接问题\n• 需要配置代理\n\n请检查 Termux 代理设置"
    
    # 成功时返回图片 URL
    return True, image_url
