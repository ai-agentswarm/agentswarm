import asyncio
import logging
from agentswarm.agents import HttpRemoteAgent, RemoteExecutionMode
from agentswarm.datamodels import Context, CompletionResponse
from shared import CalculatorInput, RemoteCompatibleStore, SilentTracing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("client")

# --- Specific Proxy Implementation ---


class CalculatorProxyAgent(HttpRemoteAgent[CalculatorInput, CompletionResponse]):
    pass


async def main():
    # 1. Setup proxy
    # Assuming worker is running on localhost:8080
    proxy = CalculatorProxyAgent(
        base_url="http://localhost:8080",
        remote_agent_id="calculator_agent",
        mode=RemoteExecutionMode.SYNC,
    )

    # 2. Setup Context with serializable components
    store = RemoteCompatibleStore()
    tracing = SilentTracing()
    context = Context(
        trace_id="calc-trace-001", messages=[], store=store, tracing=tracing
    )

    # 3. Perform some calculations
    print("\n--- 🧮 Remote Calculation Example ---")

    # Addition
    logger.info("Requesting 10 + 5...")
    input_add = CalculatorInput(operation="add", a=10, b=5)
    result = await proxy.execute("user-42", context, input=input_add)
    print(f"Result 1: {result.value}")

    # Verify store update
    print(f"Sub-result stored in blackboard: {context.store.get('last_result')}")

    # Multiplication (using the result from previous step?)
    logger.info("Requesting Result * 2...")
    last_res = context.store.get("last_result")
    input_mul = CalculatorInput(operation="mul", a=last_res, b=2)
    result = await proxy.execute("user-42", context, input=input_mul)
    print(f"Result 2: {result.value}")
    print(f"Final result stored in blackboard: {context.store.get('last_result')}")


if __name__ == "__main__":
    import sys
    import os

    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)

    try:
        asyncio.run(main())
    except ConnectionError:
        print(
            "\n❌ Error: Could not connect to worker. Please start 'worker.py' first in another terminal."
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
