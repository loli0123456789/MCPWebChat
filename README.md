
<h1 align="center">MCP Web Chat</h1 >


<div align="center">

[功能介绍](#功能介绍) | [环境构建](#环境构建) | [应用相关说明](#应用相关说明) | [启动脚本](#启动脚本)

</div>


# 功能介绍
- 可以调用MCP进行WebChat，解决了MCP Server长期连接可能中断的问题
- 可以创建包括通用方法的MCP Server
- 可以创建包装业务api的MCP Server


# 环境构建
创建python虚拟环境：

conda create -n mcp python=3.12

conda activate mcp

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 

## 错误情况处理
如果提示numpy需要特定版本才行，最新版本安装报错
pip install numpy==1.26.0 -i https://pypi.tuna.tsinghua.edu.cn/simple


# 应用相关说明

## env配置
需要配置大模型apikey

需要配置高德地图mcp server的key（高德官网申请即可，有免费调用量可用）

## 主程序
端口：10001

## 模拟业务api

端口：10002

运行：python mcp_server/test_api.py

## MCP Server

- common mcp server

端口：9001

运行：python mcp_server/common_server.py

- business mcp server

端口：9002

运行：python mcp_server/business_server.py

## 应用运行顺序

先test_api，再business mcp server，common mcp server

最后运行主程序


# 启动脚本

激活虚拟环境

conda activate mcp

Linux服务器后台方式自动运行

nohup python app.py > output.log 2>&1 &

jobs -l       # 查看后台任务（仅当前终端有效）

查看进程ID

ps aux | grep app.py  # 查看进程ID（PID）

结束进程

kill -9 <PID>  # 强制终止（替换<PID>为实际进程ID）

查询日志

tail -f output.log

## ip冲突检查
lsof -i :15001
kill -9 pid


# 关于MCP Client的问题

## 过程
如果直接在每次api请求的时候启动MCP Client，那么MCP Client会在请求结束的时候中断报错
所以，我在调用完，直接就关闭了MCP Client

但是，当我api接口调整为流式输出的时候，这样也不行了

于是，改为是程序启动的时候，启动MCP Client，但是如果隔一段时间，MCP Client就中断了，没法调用
于是，加了心跳检测，定时ping，但还是会有问题，可以ping但是调用还是不行
于是，给Fastapi本身也加了心跳检测

还是不行，于是调整为定期重启MCP Client，依然会有问题，会导致后续重启不来

或者都写到定时重启的task中？---- 也不行

现在可以使用的是：每次只是启动，不关闭之前的 --- 问题就是心跳越来越多

再试试，不启动也不关闭？

再一个利用uvicorn的reload，定时修改文件，触发程序重启 --- xx，会产生其他问题，而且生产也不推荐

## 解决
使用百度的appbuilder mcp client，人家内部已经封装好，可以很方便的实现client的调用

报错一直是关于cancelscope的，于是在调用之前创建task_group，把sse_client的调用给包起来，避免向外传导

相关代码见：mcp_cll/mcp_host.py initialize方法


## 关于MCP生命周期的问题
- 每次对话生成MCP Client
存在过于频繁连接的问题

- 程序初始化生成MCP Client
如果MCP很多，存在资源浪费的情况，一直不用但是需要一开始加载，而且后续还需要更新呢
存在长时间连接连接失效的问题，还需要定时刷新

- 一次会话生成MCP Client，可能更为合适？
可以根据需要，启动需要的MCP Client
也会存在一直不用，MCP失效端口的问题
还得考虑出问题后重启

## 最新情况
host 全局唯一维护mcp client连接
另外由于有些client可能有雨server端控制，一段时间不用会断开，因此使用心跳定时ping

mcp_chat 专职chat，并通过host获取与调用mcp tool

后续需要一个client池子？按需加载，没有则加载，有则直接使用。
目前暂未处理，连接失败重连的情况


# 社区交流互动

欢迎关注公众号，交流、获取更多信息

![公众号二维码](wx.jpg "公众号二维码")