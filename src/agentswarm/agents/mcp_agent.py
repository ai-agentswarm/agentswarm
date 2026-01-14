import asyncio
from typing import List, Optional, Any, Dict
from abc import abstractmethod
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool 

from .base_agent import BaseAgent
from ..datamodels import Context

class MCPToolAgent(BaseAgent[dict, Any]):
    """
    An agent that wraps a specific tool from an MCP server.
    """
    def __init__(self, session: ClientSession, tool: Tool):
        self._session = session
        self._tool = tool

    def id(self) -> str:
        return self._tool.name

    def description(self, user_id: str) -> str:
        return self._tool.description or f"Tool {self._tool.name} from MCP server"

    def input_parameters(self) -> dict:
        # MCP tools define inputSchema in a way compatible with JSON Schema
        schema = self._tool.inputSchema
        if schema:
             # Ensure title is removed if present as per convention in other agents, though optional
            schema.pop('title', None)
            return schema
        return {}

    def output_parameters(self) -> dict:
        # MCP tools return generic content lists (text, images, etc.)
        # We don't have a strict schema for the output content structure here yet
        return {"type": "object", "description": "The result of the tool execution"}

    async def execute(self, user_id: str, context: Context, input: dict = None) -> Any:
        if input is None:
            input = {}
        
        # Call the tool on the MCP server
        result = await self._session.call_tool(self._tool.name, arguments=input)
        
        # Process result.content which is a list of TextContent | ImageContent | EmbeddedResource
        # For simplicity, we return the raw list or a simplified text representation
        # depending on what the framework expects. BaseAgent expects output_type.
        # Since we defined OutputType as Any, we return the result object or content.
        return result.content

class MCPBaseAgent:
    """
    A base class for connecting to an MCP server and discovering tools.
    This acts as a factory/manager for MCPToolAgents.
    """
    
    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._exit_stack = None

    @abstractmethod
    def get_server_params(self) -> StdioServerParameters:
        """
        Define the connection parameters for the MCP server.
        """
        pass

    @asynccontextmanager
    async def connect(self):
        """
        Async context manager to establish connection to the MCP server.
        """
        server_params = self.get_server_params()
        
        # We manually manage the nested context managers to keep the session alive appropriately
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self._session = session
                await session.initialize()
                yield self
                self._session = None

    async def get_agents(self) -> List[MCPToolAgent]:
        """
        Discovers tools on the connected MCP server and returns them as a list of MCPToolAgent.
        Must be called within the 'connect' context.
        """
        if not self._session:
            raise RuntimeError("MCP session is not active. Use 'async with agent.connect():'")
        
        response = await self._session.list_tools()
        agents = []
        for tool in response.tools:
            agents.append(MCPToolAgent(self._session, tool))
        
        return agents
