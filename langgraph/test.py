import asyncio
from fastmcp.client import Client
from langchain.mcp import MCPAdapter

async def main():
    async with MCPAdapter(Client("https://mcp.notion.com/mcp", auth="oauth")) as adapter:
        tools = await adapter.list_tools()
        print([t.name for t in tools])

asyncio.run(main())