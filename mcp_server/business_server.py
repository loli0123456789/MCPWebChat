import asyncio
import os
import sys
import aiohttp
from mcp.server.fastmcp import FastMCP

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.shared._httpx_utils import create_mcp_http_client

import datetime

import requests

from inspect import Parameter, Signature

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_call.mcp_utils import post_form_data

# mcp = FastMCP(
#     name="myMCP",
#     host="0.0.0.0",
#     port=9002,
#     description="动态mcp",
#     sse_path="/sse",
#     server_class=Server
# )

mcp = Server("business mcp server")


# 此处只是示例，实际可用业务系统或apidoc获取
api_configs = [
    {
        "name": "get_bmi",
        "discription": "获取BMI指数",
        "api_url": "http://127.0.0.1:10002/get_bmi",
        "input_params": """height_m|体重（千克）|必填
        weight_kg|体重（千克）|必填
        """
    },
    {
        "name": "get_recrangel_area",
        "discription": "获取矩形面积",
        "api_url": "http://127.0.0.1:10002/get_recrangel_area",
        "input_params": """height|身高（厘米）|必填
        width|宽度（厘米）|必填
        """
    }
]


def process_input_param(input_param: str):
    """
    处理输入参数
    """

    required = []
    properties = {}

    rows = input_param.split("\n")
    for row in rows:
        fields = row.split("|")
        code = ""
        description = ""
        is_required = ""

        if len(fields) > 0:
            code = fields[0]
        code = code.strip()

        if code == "参数":
            continue

        if len(fields) > 1:
            description = fields[1]
        description = description.strip()

        if len(fields) > 2:
            is_required = fields[2]
        is_required = is_required.strip()

        if is_required == "必填" or is_required == "是":
            required.append(code)

        properties[code] = {"type": "string", "description": description}

    return {"type": "object", "properties": properties, "required": required}


async def init_tools():
    
    tools = []
    for api in api_configs:
        # 编码，可作为tool名称
        code = api.get("name", "")
        # 方法描述
        description = api.get("discription", "")
        # 实际调用接口地址
        api_url = api.get("api_url", "")
        # 入参
        input_params = api.get("input_params", "")

        tool = types.Tool(
            name=code,
            description=description,
            inputSchema=process_input_param(input_params),
        )
        tools.append(tool)

    return tools


@mcp.list_tools()
async def list_tools() -> list[types.Tool]:

    tools = await init_tools()

    return tools


async def request_api(name: str, arguments: dict):
    """请求api"""

    api_url = ""

    for api in api_configs:
        if api["name"] == name:
            api_url = api["api_url"]
            break
    else:
        raise ValueError(f"Unknown tool: {name}")

    result = await post_form_data(api_url, arguments, access_token=None)

    return result


@mcp.call_tool()
async def fetch_tool(name: str, arguments: dict) -> list[types.Content]:

    print(f"name: {name}")
    print(f"arguments: {arguments}")

    result = await request_api(name, arguments)

    return [types.TextContent(type="text", text=result)]


if __name__ == "__main__":
    # 初始化并运行服务器
    try:

        # get_agent_list()

        # register_dynamic_tools(mcp, functions_config)

        # print("Starting server...")
        # mcp.run(transport="sse")
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await mcp.run(
                    streams[0], streams[1], mcp.create_initialization_options()
                )
            return Response()

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn

        uvicorn.run(starlette_app, host="127.0.0.1", port=9002)

    except Exception as e:
        print(f"Error: {e}")
