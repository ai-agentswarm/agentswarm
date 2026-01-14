# Model Context Protocol (MCP) Support

Agentswarm provides native support for the [Model Context Protocol](https://github.com/modelcontextprotocol), allowing you to connect your agents to a vast ecosystem of external tools and data sources.

## How it Works

1.  **MCPBaseAgent**: Manages the connection to an MCP server (e.g., via stdio).
2.  **MCPToolAgent**: Automatically wraps each tool exposed by the server into a standard `BaseAgent`.

## API Reference

### MCPBaseAgent

::: agentswarm.agents.MCPBaseAgent

### MCPToolAgent

::: agentswarm.agents.MCPToolAgent

## Example Usage

```python
from agentswarm.agents import MCPBaseAgent
from mcp import StdioServerParameters

class MyMCP(MCPBaseAgent):
    def get_server_params(self):
        return StdioServerParameters(command="uvx", args=["mcp-server-sqlite", ...])

async def main():
    factory = MyMCP()
    async with factory.connect() as agent_manager:
        tools = await agent_manager.get_agents()
        # tools is a list of MCPToolAgent instances you can now use!
```
