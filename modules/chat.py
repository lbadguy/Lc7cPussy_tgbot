"""
AI 对话模块 - 使用 Antigravity Manager 反代（google-genai 新 SDK）
"""
import logging

import config

logger = logging.getLogger(__name__)

# Gemini 客户端
client = None
GENAI_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("google-genai 库未安装，AI 对话功能不可用")


def init_client():
    """初始化 Gemini 客户端"""
    global client
    
    if not GENAI_AVAILABLE:
        return False
    
    # 确保 URL 不含 /v1 后缀
    base_url = config.ANTIGRAVITY_BASE_URL.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    
    client = genai.Client(
        api_key=config.ANTIGRAVITY_API_KEY,
        http_options=types.HttpOptions(
            base_url=base_url,
            timeout=30000,  # 30 秒超时（毫秒）
        )
    )
    logger.info(f"Gemini 客户端已配置: {base_url}")
    return True


async def test_connection() -> tuple[bool, str]:
    """测试 API 连接"""
    if not GENAI_AVAILABLE:
        return False, "❌ AI 功能不可用（未安装 google-genai 库）"
    
    if not client:
        return False, "❌ AI 客户端未初始化"
    
    try:
        response = client.models.generate_content(
            model=config.DEFAULT_MODEL,
            contents="hi",
        )
        return True, f"✅ API 连接成功！模型: {config.DEFAULT_MODEL}"
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "unavailable" in error_msg.lower():
            return False, "❌ API 服务不可用。请确保 Antigravity Manager 正在运行。"
        elif "connection" in error_msg.lower():
            return False, "❌ 无法连接到 Antigravity Manager。"
        else:
            return False, f"❌ API 错误: {error_msg[:200]}"


# 用户聊天会话缓存
_chat_sessions = {}  # {user_id: chat_session}


def get_or_create_chat(user_id: int, model: str) -> object:
    """获取或创建用户的聊天会话"""
    key = f"{user_id}_{model}"
    if key not in _chat_sessions:
        _chat_sessions[key] = client.chats.create(
            model=model,
            config={'automatic_function_calling': {'disable': True}}
        )
    return _chat_sessions[key]


def reset_chat(user_id: int):
    """重置用户的聊天会话"""
    keys_to_remove = [k for k in _chat_sessions if k.startswith(f"{user_id}_")]
    for key in keys_to_remove:
        del _chat_sessions[key]


def chat(messages: list[dict], model: str = None, user_id: int = None) -> str:
    """发送消息并获取回复"""
    if not GENAI_AVAILABLE:
        raise RuntimeError("AI 功能不可用（未安装 google-genai）")
    
    if not client:
        raise RuntimeError("AI 客户端未初始化")
    
    use_model = model or config.DEFAULT_MODEL
    
    try:
        # 获取最后一条用户消息
        user_message = messages[-1]["content"] if messages else ""
        
        if user_id:
            # 使用 chat session（自动管理历史）
            chat_session = get_or_create_chat(user_id, use_model)
            response = chat_session.send_message(user_message)
        else:
            # 无 user_id，直接生成
            response = client.models.generate_content(
                model=use_model,
                contents=user_message,
                config={'automatic_function_calling': {'disable': True}}
            )
        
        # 获取回复文本
        text = response.text
        
        if not text:
            logger.warning(f"AI 返回空响应, model={use_model}")
            return "抱歉，AI 未返回有效回复，请重试或换一种方式提问。"
        
        return text
        
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "capacity" in error_msg.lower() or "unavailable" in error_msg.lower():
            raise RuntimeError(f"⚠️ 模型 {use_model} 暂时不可用（服务器容量不足）\n请用 /model 切换其他模型")
        elif "block" in error_msg.lower() or "safety" in error_msg.lower():
            return "⚠️ 该回复被安全过滤器拦截，请换一种方式提问。"
        raise


def get_model_list() -> str:
    """获取可用模型列表"""
    lines = ["🤖 **可用模型列表**\n"]
    for i, model in enumerate(config.AVAILABLE_MODELS, 1):
        marker = "✓" if model == config.DEFAULT_MODEL else " "
        lines.append(f"{marker} {i}. `{model}`")
    lines.append(f"\n当前默认: `{config.DEFAULT_MODEL}`")
    lines.append("使用 `/model [模型名]` 切换模型")
    return "\n".join(lines)


def is_valid_model(model: str) -> bool:
    """检查模型是否有效"""
    return model in config.AVAILABLE_MODELS
