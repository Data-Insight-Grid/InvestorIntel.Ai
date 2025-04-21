import asyncio, json
import shutil, os
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio
from typing import Dict, Any

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

async def google_search_with_fallback(startup_name: str, industry_name: str):
    print("Initializing MCP Google Search Agent")
    async with MCPServerStdio(
        cache_tools_list=True,
        params={
            "command": "npx",
            "args": ["-y", "@adenot/mcp-google-search"],
            "env": {
                "GOOGLE_SEARCH_ENGINE_ID": f"{GOOGLE_SEARCH_ENGINE_ID}",
                "GOOGLE_API_KEY": f"{GOOGLE_API_KEY}"
            }
        },
    ) as server:
        print("MCPServerStdio initialized")
        with trace(workflow_name="MCP Google Search"):
            print(await server.list_tools())
            searchagent: Agent = Agent(
                name="Google Search Agent",
                instructions="You are a Google Search Agent. You will receive a query and return the results in JSON format.",
                mcp_servers=[server],
                model="gpt-4o-mini"
            )
            query = f"recent news or innovations or articles of {startup_name} or {industry_name}"
            results = await Runner.run(searchagent, query)
            print("Results:", results.final_output)
            return {"results": results.final_output}

if __name__ == "__main__":
    print(asyncio.run(google_search_with_fallback("Elon Musk", "AI")))
