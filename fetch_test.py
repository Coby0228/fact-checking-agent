import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TEST_URL = "https://example.com"
async def test_server():
    # 連接到 MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server_fetch"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化
            await session.initialize()
            
            # 列出可用的 tools
            tools = await session.list_tools()
            print("Available tools:", tools)
            
            # 測試 fetch tool
            result = await session.call_tool("fetch", {
                "url": TEST_URL
            })
            print("Fetch result:", result)

# 執行測試
asyncio.run(test_server())