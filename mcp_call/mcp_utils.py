import aiohttp

def format_tools_for_llm(tool) -> str:
    """对tool进行格式化
    Returns:
        格式化之后的tool描述
    """
    args_desc = []
    if "properties" in tool.inputSchema:
        for param_name, param_info in tool.inputSchema["properties"].items():
            arg_desc = (
                f"- {param_name}: {param_info.get('description', 'No description')}"
            )
            if param_name in tool.inputSchema.get("required", []):
                arg_desc += " (required)"
            args_desc.append(arg_desc)

    return f"Tool: {tool.name}\nDescription: {tool.description}\nArguments:\n{chr(10).join(args_desc)}"


def convert_mcp_tool_to_openai_tool(mcp_tool):
    """将 MCP 工具转换为 OpenAI 的 function call 格式"""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.inputSchema,
        },
    }
    
    
async def post_form_data(url, args: dict, access_token: str):
    # 目标URL
    # 测试用的API，会返回你发送的数据

    json_data = {}

    for key, value in args.items():
        json_data[key] = value

    headers = {}

    async with aiohttp.ClientSession() as session:
        try:
            # 发送POST请求
            async with session.post(url, json=json_data, headers=headers) as response:
                # 获取响应状态码
                print(f"Status: {response.status}")

                # 获取响应文本（JSON或其他格式）
                response_data = await response.text()
                # print(f"Response: {response_data}")

                return response_data

        except Exception as e:
            print(f"Error: {e}")
