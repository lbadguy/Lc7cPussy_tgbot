"""
AI 对话模块 - 使用 Antigravity Manager 反代（Gemini 协议）
"""
import logging
import warnings

import config

logger = logging.getLogger(__name__)

# Gemini 客户端
GENAI_AVAILABLE = False

# 抑制弃用警告（Antigravity Tools 官方使用此库）
warnings.filterwarnings("ignore", message=".*google.generativeai.*", category=FutureWarning)

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("google-generativeai 库未安装，AI 对话功能不可用")


def init_client():
    """初始化 Gemini 客户端"""
    if not GENAI_AVAILABLE:
        return False
    
    # 确保 URL 不含 /v1 后缀（Gemini 协议使用 /v1beta/）
    base_url = config.ANTIGRAVITY_BASE_URL.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    
    genai.configure(
        api_key=config.ANTIGRAVITY_API_KEY,
        transport="rest",
        client_options={'api_endpoint': base_url}
    )
    logger.info(f"Gemini 客户端已配置: {base_url}")
    return True


async def test_connection() -> tuple[bool, str]:
    """测试 API 连接"""
    if not GENAI_AVAILABLE:
        return False, "❌ AI 功能不可用（未安装 google-generativeai 库）"
    
    try:
        model = genai.GenerativeModel(config.DEFAULT_MODEL)
        response = model.generate_content(
            "hi",
            request_options={"timeout": 15}
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


def _convert_history(messages: list[dict]) -> tuple[list[dict], str]:
    """将 OpenAI 格式的历史转换为 Gemini 格式
    
    输入: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    输出: (gemini_history, last_user_message)
    
    Gemini 格式: [{"role": "user", "parts": ["..."]}, {"role": "model", "parts": ["..."]}]
    """
    if not messages:
        return [], ""
    
    # 最后一条消息是当前用户输入
    last_msg = messages[-1]["content"]
    
    # 之前的消息作为历史
    history = []
    for msg in messages[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    
    return history, last_msg


def chat(messages: list[dict], model: str = None) -> str:
    """发送消息并获取回复"""
    if not GENAI_AVAILABLE:
        raise RuntimeError("AI 功能不可用（未安装 google-generativeai）")
    
    use_model = model or config.DEFAULT_MODEL
    
    try:
        # 转换历史格式
        history, user_message = _convert_history(messages)
        
        # 创建模型和对话
        gmodel = genai.GenerativeModel(use_model)
        
        if history:
            # 有历史记录，使用 chat 模式
            conversation = gmodel.start_chat(history=history)
            response = conversation.send_message(
                user_message,
                request_options={"timeout": 30}
            )
        else:
            # 无历史，直接生成
            response = gmodel.generate_content(
                user_message,
                request_options={"timeout": 30}
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
