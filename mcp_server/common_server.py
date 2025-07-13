import os
import sys
import aiohttp
from mcp.server.fastmcp import FastMCP
import datetime


mcp = FastMCP(
    name="common MCP Server",
    host="0.0.0.0",
    port=9001,
    description="common MCP Server",
    sse_path="/sse",
)


@mcp.tool()
def get_time() -> str:
    """获取当前系统时间"""
    return str(datetime.datetime.now())


async def fetch_website(
    url: str,
) -> str:
    """获取网页内容"""

    headers = {"User-Agent": "common MCP Server"}

    async with aiohttp.ClientSession() as session:
        try:
            # 发送POST请求
            async with session.get(url, headers=headers) as response:
                # 获取响应状态码
                print(f"Status: {response.status}")

                # 获取响应文本（JSON或其他格式）
                response_data = await response.text()
                # print(f"Response: {response_data}")

                return response_data

        except Exception as e:
            print(f"Error: {e}")


mcp.add_tool(fetch_website)


if __name__ == "__main__":
    # 初始化并运行服务器
    try:
        print("Starting server...")
        mcp.run(transport="sse")
    except Exception as e:
        print(f"Error: {e}")
