import asyncio
import json
import os
import sys
import traceback
from openai import AsyncOpenAI
from typing import Optional, Any, Dict, Union, AsyncGenerator


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from mcp_call.mcp_host import Host
from mcp_call.mcp_utils import convert_mcp_tool_to_openai_tool
from utils.log import log
from utils.sys_env import get_env

class MCP_Chat:

    def __init__(self, host, history=[]):

        base_url = os.getenv("QWEN_BASE_URL")
        api_key = os.getenv("QWEN_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        mcp_model = get_env("DEFAULT_MCP_MODEL")
        self.model = mcp_model

        self.messages = []
        self.host = host
        # 历史消息记录
        if history:
            self.messages.extend(history)

    async def chat(self, prompt, role="user"):
        """与LLM进行交互，返回包含 tool_call 的完整响应"""
        if prompt != "":
            self.messages.append({"role": role, "content": prompt})

        if len(self.host.f_tools) > 0:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.host.f_tools,  # 使用工具定义
                stream=True,
                tool_choice="auto",  # 或者指定具体工具名
                extra_body={"enable_thinking": False},
            )
            # 去掉思考模型，响应速度更快

        # 避免没有获取到tools的情况报错
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True,
                tool_choice="auto",  # 或者指定具体工具名
            )

        return response

    async def find_client_tool(self, tool_name: str):
        """查找客户端工具"""
        target_client = None
        target_tool = None
        for client in self.host.mcp_clients:
            tools = client.tools
            for tool in tools:
                if tool.name == tool_name:
                    target_client = client
                    target_tool = tool
                    break

            if target_tool:
                break

        return target_client, target_tool

    async def exec_tool(
        self, tool_name, tool_args
    ) -> AsyncGenerator[Dict[str, Any], None]:
        target_client, target_tool = await self.find_client_tool(tool_name)

        if target_client != None and target_tool != None:
            try:
                # print(f"[工具调用]：正在调用工具 {tool_name}")

                yield {
                    "type": "tool_start",
                    "content": f"[工具调用]：正在调用工具 {tool_name}，参数：{tool_args}\n",
                }

                result = await target_client.session.call_tool(tool_name, tool_args)

                if isinstance(result, dict) and "progress" in result:
                    progress = result["progress"]
                    total = result["total"]
                    percentage = (progress / total) * 100
                    # Yield progress update
                    yield {
                        "type": "progress",
                        "progress": progress,
                        "total": total,
                        "percentage": round(percentage, 1),
                        "message": f"Progress: {progress}/{total} ({percentage:.1f}%)",
                    }

                result = result.content[0].text
                # print(f"[工具执行结果]: {result}")

                yield {"type": "tool_finish", "content": "[工具执行结果]：\n"}

                # Yield final result
                yield {"type": "tool_result", "content": result + "\n"}

            except Exception as e:
                error_info = e.args[0] if e.args else repr(e)
                error_msg = f"[工具调用出错]：{error_info}\n"
                # traceback.print_exc()
                yield {"type": "error", "content": error_msg}

        else:
            error_msg = f"No server found with tool: {tool_name}"
            log.info(error_msg)
            yield {"type": "error", "content": error_msg}

    async def chat_loop(self, input) -> AsyncGenerator[Dict[str, Any], None]:
        """运行交互式聊天循环"""

        response = await self.chat(input)

        while True:
            tool_call_response = False
            function_name, args, text = "", "", ""
            tool_call = {}
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    tool_call_response = True
                    if not function_name:
                        function_name = delta.tool_calls[0].function.name
                    args_delta = delta.tool_calls[0].function.arguments
                    # print(args_delta)  # 打印每次得到的数据
                    if args_delta:  # 追加
                        args = args + args_delta
                elif delta.content:
                    tool_call_response = False

                    text_delta = delta.content
                    yield {"type": "result", "content": text_delta}
                    # text = text + text_delta

            if tool_call_response:
                # tool_call = tool_call
                tool_name = function_name
                log.info(f"调用工具：{tool_name}, 参数：{args}")

                tool_args = json.loads(args)
                tool_call.function.name = function_name
                tool_call.function.arguments = args

                # 执行工具并处理流式输出
                async for event in self.exec_tool(tool_name, tool_args):
                    # 如果是进度更新，则直接发送
                    if event["type"] == "progress":
                        yield event
                    elif event["type"] == "error":
                        # 错误情况下也返回错误信息
                        yield event
                        return
                    elif (
                        event["type"] == "tool_start" or event["type"] == "tool_finish"
                    ):
                        # 开始、完成调用
                        yield event
                    else:
                        # 输出最终结果
                        # 添加 tool_call 和 tool_response 到 messages
                        self.messages.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [tool_call.model_dump()],
                            }
                        )

                        # 添加 tool_response 到 messages
                        self.messages.append(
                            {
                                "role": "tool",
                                "name": tool_call.function.name,
                                "content": str(event["content"]),
                            }
                        )

                        yield event

                response = await self.chat("")

            else:
                break


async def main():
    host = None
    try:

        host = Host()
        await host.connect_mcp_servers()

        mcp_chat = MCP_Chat(host)
        # input = "查下北京的天气，再告诉我怎么从天安门去故宫"
        # await host.chat_loop("查下北京的天气，再告诉我怎么从天安门去故宫")

        # 改为可以多次对话
        while True:
            user_input = input("请输入：")

            if user_input == "/x":
                break

            async for event in mcp_chat.chat_loop(user_input):
                print(event)

    except Exception as e:
        log.error(f"主程序发生错误: {type(e).__name__}: {e}")
        # 打印完整的调用堆栈
        traceback.print_exc()
    finally:
        # 无论如何，最后都要尝试断开连接并清理资源
        log.info("\n正在关闭客户端...")
        await host.disconnect_mcp_servers()
        log.info("客户端已关闭。")


if __name__ == "__main__":
    # 我要去济南奥体中心出差，请你查询附近5km的酒店，为我安排行程
    asyncio.run(main())
