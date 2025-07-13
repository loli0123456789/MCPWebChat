import asyncio
import json
import os
import sys
import traceback

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.schemas import ApiResponse
from utils.enums import ChatRole, ErrCode, LLMRole

from utils.log import log

from services.message import (
    save_chat_history,
    get_message_history,
    update_chat_history,
)

from mcp_call.mcp_chat import MCP_Chat
from models.conversation import ConversationRepository


router = APIRouter(prefix="", tags=["对话消息"])


@router.post("/conversation/add")
async def add_conversation(
    request: Request, access_token: str = Header(None, alias="accessToken")
):
    """
    新增会话
    """
    # 获取 form-data
    form_data = await request.form()
    # 单独获取某个字段
    agent_id = form_data.get("agentId")
    conversation_name = form_data.get("conversationName")
    user_id = form_data.get("userId")

    repo = ConversationRepository()
    conversation_id = await repo.add_conversation(
        agent_id, conversation_name, user_id
    )

    content = ApiResponse(
        errCode=ErrCode.SUCCESS.value, errMsg="", data=conversation_id, playload=""
    )
    return JSONResponse(
        content=content.model_dump(), headers={"X-Response-Type": "ApiResponse"}
    )


# 全局变量用于跟踪请求状态
request_states = {}
request_states_lock = asyncio.Lock()

Common_Agent_ID = "common"



@router.post("/chat")
async def chat(request: Request, access_token: str = Header(None, alias="accessToken")):
    """
    对话
    """
    data = await request.json()
    user_message = data.get("message", "")
    chat_type = data.get("chatType", "agent")  # 默认为agent

    # 交易（Agent）ID，用于动态获取交易接口地址
    # 会话ID，用于写入历史消息记录
    agent_id = data.get("agentId", "")
    session_id = data.get("sessionId", "")
    user_id = data.get("userId", "")
    # remote_url = data.get("remoteUrl", None)

    user_message_id = ""
    parent_id = ""

    # 记录消息到文件
    if session_id:
        user_message_id = await save_chat_history(
            agent_id,
            session_id,
            user_id,
            ChatRole.USER.value,
            user_message,
            access_token=access_token,
        )


    # 生成唯一请求 ID
    request_id = id(request)
    request_id = str(request_id)
    new_message_id = ""
    # 键值对需要保证类型一直，否则后面检索不到键值
    request_states[request_id] = False

    response_temp = None
    
    response_temp = {"mcps": ["amap-amap-sse"], "input": user_message}

    if "mcps" in response_temp:

        # 从app全局变态获取host对象
        host = request.app.state.host

        # 异步生成器，用于处理流式输出
        async def generate():
            response_content = ""

            try:
                print("mcp===")

                history = await get_message_history(
                    conversation_id=session_id,
                    top_num=10,
                    add_one=1,
                    convert_type="llm",
                    access_token=access_token,
                )
                # 添加历史消息记录
                mcp_chat = MCP_Chat(host=host, history=history)

                async for event in mcp_chat.chat_loop(user_message):
                    json_data = event

                    if (
                        event["type"] == "tool_start"
                        or event["type"] == "tool_finish"
                        or event["type"] == "tool_result"
                    ):
                        # 工具调用过程，作为思考过程
                        json_data["type"] = "think"

                    elif event["type"] == "result":
                        response_content += event["content"]

                    elif event["type"] == "error":
                        # 发送错误信息
                        response_content += event["content"]

                    yield f"data: {json.dumps(json_data,ensure_ascii=False)}\n\n"

            finally:
                # 响应完成更新消息内容
                await update_chat_history(
                    new_message_id,
                    response_content,
                    access_token=access_token,
                )

            # print("disconnect")
            # await host.disconnect_mcp_servers()
            # asyncio.create_task(host.disconnect_mcp_servers())

        response = StreamingResponse(generate(), media_type="text/event-stream")
        # 添加 X-Request-ID 响应头
        response.headers["X-Request-Id"] = str(request_id)
        # 先生成response，再去执行流式，所以需要先提前生成空数据，最后再去更新！
        empty_msg = "思考中…"
        new_message_id = await save_chat_history(
            agent_id,
            session_id,
            user_id,
            ChatRole.AGENT.value,
            empty_msg,
            False,
            access_token=access_token,
            parent_id=user_message_id,
        )

        # 临时这么处理，后续需要优化
        if new_message_id == "":
            new_message_id = int(user_message_id) + 1
        if parent_id == "" or parent_id == None:
            parent_id = user_message_id
        response.headers["X-Message-Id"] = str(new_message_id)
        response.headers["X-Parent-Id"] = str(parent_id)
        return response



@router.post("/terminate_chat")
async def terminate_chat(request: Request):
    # 其实前端终止后，后端就不再执行了，而且可以通过接口的await request.is_disconnected()捕获到
    data = await request.json()
    request_id = data.get("request_id")

    async with request_states_lock:
        if request_id in request_states:
            request_states[request_id] = True
            return JSONResponse({"status": "terminated"})
        else:
            return JSONResponse({"status": "request not found"})


@router.post("/message/get_history", deprecated=True)
async def get_history(
    request: Request, access_token: str = Header(None, alias="accessToken")
):
    """
    新增会话
    """
    # 获取 form-data
    form_data = await request.form()
    # 单独获取某个字段
    conversation_id = form_data.get("conversationId")
    top_num = form_data.get("topNum")

    add_one = form_data.get("addOne")
    if add_one is None:
        add_one = 1

    convert_type = form_data.get("convertType")

    data = await get_message_history(
        conversation_id, top_num, add_one, convert_type, access_token
    )

    content = ApiResponse(
        errCode=ErrCode.SUCCESS.value, errMsg="", data=data, playload=""
    )
    return JSONResponse(
        content=content.model_dump(), headers={"X-Response-Type": "ApiResponse"}
    )

