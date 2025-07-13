import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.enums import ChatRole, LLMRole

from utils.config import Config

from models.message import MessageRepository

def parse_msgs(msgHistory):
    """
    解析前端返回消息记录，转换为提供给大模型的格式
    """
    results = []

    for msg in msgHistory:
        role = LLMRole.ASSISTANT.value if msg["role"] == "AI" else LLMRole.USER.value
        results.append({"role": role, "content": msg["content"]})

    return results


async def save_chat_history(
    agent_id,
    conversation_id,
    user_id,
    role: ChatRole,
    content,
    is_abort=False,
    access_token: str = None,
    session_id_xx="sessionId",
    chanelId="PC",
    parent_id=None,
):
    """
    保存对话记录
    """

    role = "USER" if role == ChatRole.USER.value else "AI"
    
    repo = MessageRepository()
    message_id = await repo.add_message(conversation_id, role, content)

    return message_id


async def update_chat_history(
    message_id,
    content,
    access_token: str = None,
):
    """
    更新对话记录
    """
    repo = MessageRepository()
    await repo.update_message(message_id, content)

    # print(f"{response.text}")


async def get_message_history(
    conversation_id, top_num, add_one, convert_type, access_token
):
    """
    获取消息记录
    """
    
    repo = MessageRepository()
    data = await repo.get_messages(conversation_id)

    if isinstance(data, list):
        if add_one == 1 or add_one == "1":
            # 倒序
            data.reverse()
            data = data[0 : len(data) - 1]
            # print(data)

    # 转换为llm对话格式的消息记录
    if convert_type == "llm":
        data = parse_msgs(data)
    # 转换为str格式的消息记录，直接加入到提示词
    elif convert_type == "str":
        msgs = ""
        for d in data:
            msgs += f"{d['msgType']}: {d['msg']}\n"

        data = msgs

    # print(f"{response.json()}")

    return data
