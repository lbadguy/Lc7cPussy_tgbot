"""
AI 对话模块 - 使用 Antigravity Manager 反代
"""
import logging

import config

logger = logging.getLogger(__name__)

# OpenAI 客户端（连接到 Antigravity Manager）
client = None
OPENAI_AVAILABLE = False

# 尝试导入 openai（可选依赖）
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("openai 库未安装，AI 对话功能不可用")


def init_openai_client():
    """初始化 OpenAI 客户端"""
    global client
    
    if not OPENAI_AVAILABLE:
        return None
    
    client = openai.OpenAI(
        api_key=config.ANTIGRAVITY_API_KEY,
        base_url=config.ANTIGRAVITY_BASE_URL
    )
    return client


async def test_connection() -> tuple[bool, str]:
    """测试 API 连接"""
    if not OPENAI_AVAILABLE:
        return False, "❌ AI 功能不可用（手机端未安装 openai 库）"
    
    if not client:
        return False, "❌ AI 客户端未初始化"
    
    try:
        response = client.chat.completions.create(
            model=config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10
        )
        return True, f"✅ API 连接成功！模型: {config.DEFAULT_MODEL}"
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "unhealthy" in error_msg.lower():
            return False, "❌ API 服务不可用。请确保 Antigravity Manager 正在运行。"
        elif "connection" in error_msg.lower():
            return False, "❌ 无法连接到 Antigravity Manager。"
        else:
            return False, f"❌ API 错误: {error_msg[:100]}"


def chat(messages: list[dict], model: str = None) -> str:
    """发送消息并获取回复"""
    if not OPENAI_AVAILABLE:
        raise RuntimeError("AI 功能不可用（未安装 openai）")
    
    if not client:
        raise RuntimeError("AI 客户端未初始化")
    
    use_model = model or config.DEFAULT_MODEL
    
    try:
        response = client.chat.completions.create(
            model=use_model,
            messages=messages,
            timeout=60  # 60秒超时，防止卡死
        )
    except Exception as e:
        error_msg = str(e)
        if "503" in error_msg or "capacity" in error_msg.lower():
            raise RuntimeError(f"⚠️ 模型 {use_model} 暂时不可用（服务器容量不足）\n请用 /model 切换其他模型")
        raise
    
    # 获取回复内容
    choice = response.choices[0]
    content = choice.message.content
    
    # 处理空响应（如 MALFORMED_FUNCTION_CALL）
    if not content:
        finish_reason = getattr(choice, 'finish_reason', 'unknown')
        logger.warning(f"AI 返回空响应, finish_reason={finish_reason}, model={use_model}")
        
        if "FUNCTION_CALL" in str(finish_reason).upper():
            return "抱歉，我无法通过工具调用来回答这个问题。请换一种方式提问，或者直接告诉我你想知道什么。"
        return "抱歉，AI 未返回有效回复，请重试。"
    
    return content


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
