# Example: OpenAI Agents SDK with hosted/local MCP

# This is a conceptual example for the future implemented package.

from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def main():
    async with MCPServerStdio(
        params={"command": "okpdf", "args": ["serve", "--mcp", "--safe-root", "."]}
    ) as pdf_mcp:
        agent = Agent(
            name="PDF Operator",
            instructions="Use OKoffice tools to inspect, transform, and validate PDFs.",
            mcp_servers=[pdf_mcp],
        )
        result = await Runner.run(agent, "Merge a.pdf and b.pdf into merged.pdf and validate it.")
        print(result.final_output)
