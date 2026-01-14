
import asyncio
import os
from agentswarm.agents.mcp_agent import MCPBaseAgent
from mcp import StdioServerParameters
from agentswarm.datamodels import Context
from agentswarm.datamodels.local_store import LocalStore
from agentswarm.utils.tracing import Tracing

class SQLiteMCP(MCPBaseAgent):
    def get_server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command="uvx",
            args=["mcp-server-sqlite", "--db-path", "test.db"],
            env=os.environ.copy()
        )

class GitMCP(MCPBaseAgent):
    def get_server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command="uvx",
            args=["mcp-server-git", "--repository", "."],
            env=os.environ.copy()
        )

# Simple dummy tracing
class DummyTracing(Tracing):
    def trace_agent(self, *args): pass
    def trace_loop_step(self, *args): pass
    def trace_agent_result(self, *args): pass
    def trace_agent_error(self, *args): pass

async def main():
    # SQLite Example
    sqlite_factory = SQLiteMCP()
    print("--- SQLite MCP ---")
    print("Connecting to SQLite MCP Server...")
    async with sqlite_factory.connect() as agent:
        print("Connected. Discovering agents...")
        agents = await agent.get_agents()
        print(f"Discovered {len(agents)} agents.")
        
        query_agent = next((a for a in agents if a.id() == "read_query"), None)
        if query_agent:
            print("Executing read_query agent...")
            context = Context(
                trace_id="sqlite-trace",
                store=LocalStore(),
                messages=[],
                tracing=DummyTracing(), 
                thoughts=[]
            )
            write_agent = next((a for a in agents if a.id() == "write_query"), None)
            if write_agent:
                await write_agent.execute("user", context, {"query": "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)"})
                await write_agent.execute("user", context, {"query": "INSERT INTO test (name) VALUES ('Alice')"})
            
            result = await query_agent.execute("user", context, {"query": "SELECT * FROM test"})
            print(f"Result: {result}")

    # Git Example
    print("\n--- Git MCP ---")
    git_factory = GitMCP()
    print("Connecting to Git MCP Server...")
    async with git_factory.connect() as agent:
        print("Connected. Discovering agents...")
        agents = await agent.get_agents()
        print(f"Discovered {len(agents)} agents:")
        for a in agents:
            print(f"- {a.id()}")

        # Try to list files
        # The tool might be called 'list_files' or similar, let's find it 
        # Usually git mcp has 'git_status', 'git_diff', 'read_file' etc. 
        # Let's try to run 'git_status' if available.
        status_agent = next((a for a in agents if "status" in a.id()), None)
        if status_agent:
             print(f"Executing {status_agent.id()}...")
             print(f"Input params: {status_agent.input_parameters()}")
             context = Context(
                trace_id="git-trace",
                store=LocalStore(),
                messages=[],
                tracing=DummyTracing(), 
                thoughts=[]
            )
             # Provide repo_path as requested by error
             result = await status_agent.execute("user", context, {"repo_path": "."})
             print(f"Result: {result}")
        else:
             print("Status agent not found. Trying read_file for README.md...")
             read_agent = next((a for a in agents if "read_file" in a.id()), None)
             if read_agent:
                 context = Context(trace_id="git-trace", store=LocalStore(), messages=[], tracing=DummyTracing(), thoughts=[])
                 result = await read_agent.execute("user", context, {"path": "README.md"})
                 print(f"Result (truncated): {str(result)[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
