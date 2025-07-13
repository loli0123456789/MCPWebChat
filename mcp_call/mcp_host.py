import asyncio
import json
import sys
import traceback
import anyio

from appbuilder.mcp_server.client import MCPClient

from dotenv import load_dotenv

import os

from exceptiongroup import ExceptionGroup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from mcp_call.mcp_utils import convert_mcp_tool_to_openai_tool
from utils.log import log
from models.mcpserver import MCPServerRepository

load_dotenv()


def load_server_config(config_file):
    with open(config_file) as f:
        return json.load(f)


class Host:
    _instance = None

    # def __new__(cls):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #         cls._instance._initialized = False
    #     return cls._instance

    async def _start_heartbeat(self):
        """后台心跳检测任务"""
        while True:
            try:
                # 每隔 2 分钟发送一次心跳
                await asyncio.sleep(60 * 2)

                for client in self.mcp_clients:
                    if client.session:
                        await client.session.send_ping()
                        log.info(f"[心跳] 连接正常 --- ")

            except Exception as e:
                # 捕获异常并记录日志，避免任务中断
                log.error(f"心跳检测失败: {type(e).__name__}: {e}")
                traceback.print_exc()

    async def initialize(self):
        """延迟初始化（避免启动时阻塞）"""
        if not self._initialized:
            self._task_group = anyio.create_task_group()
            await self._task_group.__aenter__()
            self._task_group.start_soon(self.connect_mcp_servers)

            # await self.connect_mcp_servers()
            self._initialized = True

            # 使用 anyio 创建取消范围
            self._heartbeat_cancel_scope = anyio.CancelScope()
            self._heartbeat_task = asyncio.create_task(self._run_with_cancel_scope())

    async def _run_with_cancel_scope(self):
        """在取消范围内运行心跳任务"""
        with self._heartbeat_cancel_scope:
            await self._start_heartbeat()

    def __init__(self):

        self.mcp_clients = []

        self.all_tools = []
        self.f_tools = []

        self._initialized = False

        self._heartbeat_task = None

    async def load_mcp_servers(self, mcps=None):
        servers = {}
        try:
            repo = MCPServerRepository()
            mcp_servers = await repo.get_all_servers()

            if len(mcp_servers) > 0:
                for server in mcp_servers:
                    name = server["mcpname"]
                    url = server.get("url", "")
                    if url != "":
                        servers[name] = {
                            "url": url,
                        }
            else:
                cur_path = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(cur_path, "servers_config.json")
                server_config = load_server_config(config_file)
                servers = server_config["mcpServers"]
        except Exception as e:
            print(e)
            traceback.print_exc()

        return servers

    async def connect_mcp_servers(self, mcps=None):
        servers = await self.load_mcp_servers(mcps)

        log.info("MCP 客户端启动开始")

        # if not hasattr(self, "mcp_clients") or not self.mcp_clients:
        self.mcp_clients = []

        for name, server_info in servers.items():
            if mcps is None or name in mcps:
                try:
                    server_url = server_info["url"]

                    if name == "amap-sse":
                        key = os.getenv("AMAP_KEY")
                        server_url = server_url.replace("key=", f"key={key}")

                    log.info(f"正在连接MCP服务器: {name} {server_url}")
                    client = MCPClient()
                    await client.connect_to_server(service_url=server_url)

                    self.mcp_clients.append(client)
                    log.info(f"已连接MCP服务器: {name}")

                    tools = client.tools

                    log.info(f"mcp tool数量：{len(tools)}")

                    # self.all_tools.extend(tools)

                    for tool in tools:
                        f_tool = convert_mcp_tool_to_openai_tool(tool)
                        self.f_tools.append(f_tool)

                except Exception as e:
                    log.error(f"连接MCP服务器: {name} 失败: {type(e).__name__}: {e}")
                    # traceback.print_exc()

        log.info("MCP 客户端启动完成")

    async def disconnect_mcp_servers(self):

        try:
            log.info("正在断开MCP服务器")

            # 取消心跳任务
            if (
                hasattr(self, "_heartbeat_cancel_scope")
                and self._heartbeat_cancel_scope
            ):
                self._heartbeat_cancel_scope.cancel()

            # # 取消心跳任务
            # if self._heartbeat_task:
            #     self._heartbeat_task.cancel()

            try:
                if self._heartbeat_task:
                    await self._heartbeat_task
            except asyncio.CancelledError:
                log.info("心跳任务已取消")
            except Exception as e:
                log.error(f"取消心跳任务时出现异常: {type(e).__name__}: {e}")
                traceback.print_exc()

            self._heartbeat_task = None

            # 确保全局任务组存在
            if not hasattr(self, "_task_group") or not self._task_group:
                log.error("全局任务组不存在，无法清理客户端")
                return

            for i, client in enumerate(self.mcp_clients):
                try:
                    log.info(f"开始清理客户端 {i}")

                    # client._session_context._task_group
                    client._session_context._task_group.start_soon(client.cleanup)
                    # self._task_group.start_soon(client.cleanup)
                    log.info(f"已启动清理客户端 {i}")
                except AttributeError as e:
                    log.error(f"清理客户端 {i} 时出现属性错误: {e}")
                    traceback.print_exc()

                except Exception as e:
                    log.error(f"清理客户端 {i} 时出现异常: {type(e).__name__}: {e}")
                    traceback.print_exc()

            # 等待全局任务组完成
            if hasattr(self, "_task_group") and self._task_group:
                log.info("等待全局任务组完成")
                try:
                    self._task_group.cancel_scope.cancel()
                    await self._task_group.__aexit__(None, None, None)
                except ExceptionGroup as eg:
                    # 处理任务组中的异常组
                    log.error("任务组中发生多个异常:")
                    for exc in eg.exceptions:
                        log.error(f"- {type(exc).__name__}: {exc}")
                        traceback.print_exc()
                    # exceptions.extend(eg.exceptions)
                finally:
                    self._task_group = None

            self._initialized = False
            self.mcp_clients = []
            self.all_tools = []
            self.f_tools = []

            log.info("后台断开MCP服务器完成")

        except Exception as e:
            log.error(f"断开MCP服务器失败：{e}")
            traceback.print_exc()

    async def restart_mcp_servers(self):
        try:
            # 尝试断开连接
            await self.disconnect_mcp_servers()
        except Exception as e:
            # 捕获异常并记录日志
            log.error(f"断开MCP服务器时出现异常: {type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            log.info("尝试重新初始化MCP服务器")
            await self.initialize()
            log.info("初始化MCP服务器MCP服务器完成")
        except Exception as e:
            log.error(f"初始化MCP服务器时出现异常: {type(e).__name__}: {e}")
            traceback.print_exc()
