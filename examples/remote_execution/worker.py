import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from agentswarm.agents import BaseAgent
from agentswarm.datamodels import Context, CompletionResponse
from agentswarm.utils.remote_handler import RemoteAgentHandler
from shared import CalculatorInput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

# --- Practical Agent Implementation ---


class CalculatorAgent(BaseAgent[CalculatorInput, CompletionResponse]):
    def id(self) -> str:
        return "calculator_agent"

    def description(self, user_id: str) -> str:
        return "A simple calculator agent."

    async def execute(
        self, user_id: str, context: Context, input: CalculatorInput = None
    ) -> CompletionResponse:
        logger.info(f"Executing calculation: {input.operation}({input.a}, {input.b})")

        if input.operation == "add":
            res = input.a + input.b
        elif input.operation == "sub":
            res = input.a - input.b
        elif input.operation == "mul":
            res = input.a * input.b
        elif input.operation == "div":
            res = input.a / input.b if input.b != 0 else float("inf")
        else:
            res = 0

        # Store result in blackboard for demonstration
        context.store.set("last_result", res)

        return CompletionResponse(value=f"The result is {res}")


# --- protocol implementation ---


class RemoteAgentHTTPRequestHandler(BaseHTTPRequestHandler):
    handler: RemoteAgentHandler = None

    def do_POST(self):
        if self.path == "/execute":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode("utf-8"))

            logger.info(
                f"Received execution request for agent: {payload.get('agent_id')}"
            )

            try:
                # We need to run the async handler in the sync http server
                import asyncio

                result = asyncio.run(self.handler.handle_execute(payload))

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_worker(port=8080):
    # Register agents
    agent = CalculatorAgent()
    handler = RemoteAgentHandler(agents=[agent])
    RemoteAgentHTTPRequestHandler.handler = handler

    server_address = ("", port)
    httpd = HTTPServer(server_address, RemoteAgentHTTPRequestHandler)
    logger.info(f"Worker starting on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Worker stopping...")
        httpd.server_close()


if __name__ == "__main__":
    # We need to fix Context and Message imports because of how serialization works
    import sys
    import os

    # Add project root to path so shared and other imports work
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)

    run_worker()
