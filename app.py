import asyncio
import os
import anyio
from fastapi import Depends, FastAPI, Header, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
import argparse
import httpx


from schemas.schemas import ApiResponse
from utils.enums import ErrCode, LLMRole
from utils.log import log

from mcp_call.mcp_host import Host


# 定义 lifespan 事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行的代码
    print("Starting up...")

    # 定义全局host用于连接mcp
    # await host.initialize()

    asyncio.create_task(background_restart_mcp_servers())

    yield

    await host.disconnect_mcp_servers()

    # 关闭时执行的代码
    print("Shutting down...")



app = FastAPI(lifespan=lifespan)

# 全局Host实例
host = Host()
app.state.host = host


from routes.message_route import router as message_router


app.include_router(message_router)


# 允许跨域（重要！）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    # 这里设置了，前端才可以取到（跨域限制）
    expose_headers=["X-Response-Type", "X-Message-Id", "X-Parent-Id", "X-Request-Id"],
)


# 基础中间件（仅处理静态文件）
@app.middleware("http")
async def base_middleware(request: Request, call_next):
    response = await call_next(request)
    # 跳过静态文件
    if request.url.path.startswith("/static"):
        return response

    # 检查是否有自定义头字段 X-Response-Type
    if response.headers.get("X-Response-Type") == "ApiResponse":
        print("Custom ApiResponse detected in middleware")

    return response


# 全局异常处理器：处理 HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            errCode=(
                ErrCode.TOKEN.value
                if exc.status_code == 401
                and exc.headers.get("X-Error-Code") == str(ErrCode.TOKEN.value)
                else (
                    ErrCode.FAILURE.value
                    if exc.status_code >= 500
                    else ErrCode.INPUT.value
                )
            ),
            errMsg=exc.detail,
            data={},
            playload="",
        ).model_dump(),
    )


# 全局异常处理器：处理请求验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content=ApiResponse(
            errCode=ErrCode.INPUT.value,
            errMsg="Validation error",
            data={"errors": exc.errors()},
            playload="",
        ).model_dump(),
    )


# 全局异常处理器：处理其他未捕获异常
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            errCode=ErrCode.EXCEPTION.value, errMsg=str(exc), data={}, playload=""
        ).model_dump(),
    )


# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


# 定义根路径返回 index.html
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """检测服务是否正常"""
    return {"status": "ok"}


async def background_keepalive():
    while True:
        try:

            await asyncio.sleep(60 * 5)

            # 模拟请求（实际可调用内部接口）
            async with httpx.AsyncClient() as client:
                await client.get("http://127.0.0.1:10001/health")
                log.info("[心跳] helth check success")

        except Exception as e:
            print(f"后台心跳失败: {e}")
            await asyncio.sleep(5)  # 失败后重试


from utils.sys_env import get_env

mcp_restart_minutes = float(get_env("MCP_RESTART_MINUTES", 60))


async def background_restart_mcp_servers():
    while True:
        try:

            log.info("后台重启MCP服务器开始")

            try:
                await host.restart_mcp_servers()

            except Exception as e:
                print(f"后台重启MCP服务器失败: {e}")
                await asyncio.sleep(5)

            log.info("后台重启MCP服务器完成")

            await asyncio.sleep(60 * mcp_restart_minutes)

        except Exception as e:
            print(f"后台重启MCP服务器失败: {e}")
            await asyncio.sleep(5)  # 失败后重试


# 增加大模型转发服务
# 方便跟踪模型调用参数
TARGET_URL = "https://dashscope.aliyuncs.com/compatible-mode"  # 替换成你的真实 API 地址（如 http://localhost:8000）


@app.api_route("/v1/{path:path}", methods=["POST", "GET", "PUT", "DELETE"])
async def proxy_openai(request: Request, path: str):
    # 1. 打印原始请求信息（调试用）
    headers = dict(request.headers)
    body = await request.body()
    log.info(f"📤 请求 Headers: {headers}")
    log.info(f"📤 请求 Body: {body.decode()}")

    # 2. 移除 Host 头（避免目标服务器拒绝）
    headers.pop("host", None)

    # 3. 透传请求到目标大模型
    try:
        async with httpx.AsyncClient() as client:
            # 构建目标 URL（保持 OpenAI 标准路径 /v1/...）
            target_url = f"{TARGET_URL}/v1/{path}"

            # 透传请求
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
                timeout=60.0,
            )
            response.raise_for_status()  # 检查 HTTP 错误

            # 4. 如果是流式响应（如 chat/completions），直接返回 StreamingResponse
            if "text/event-stream" in response.headers.get("content-type", ""):
                return StreamingResponse(
                    response.aiter_bytes(),
                    media_type=response.headers["content-type"],
                    status_code=response.status_code,
                )

            # 5. 非流式响应，直接返回 JSON
            log.info(f"📥 响应 Body: {response.text}")
            return response.json()

    except Exception as e:
        log.error(f"🚨 代理错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 命令行参数解析
parser = argparse.ArgumentParser(description="Start param")
parser.add_argument(
    "-p", "--port", type=int, nargs="?", default=10001, help="Set start port"
)


if __name__ == "__main__":
    args = parser.parse_args()
    port = args.port

    # 使用 Uvicorn 启动应用
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
