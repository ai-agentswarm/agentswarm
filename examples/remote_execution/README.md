# Advanced Remote Execution Example

This example demonstrates how to execute an agent remotely using a real HTTP server and the Proxy pattern.

## Components

- **`shared.py`**: Contains serializable models (`CalculatorInput`) and components (`RemoteCompatibleStore`, `SilentTracing`) shared between the client and the worker.
- **`worker.py`**: Implements a simple HTTP server (using `http.server`) that listens for agent execution requests and runs the real `CalculatorAgent`.
- **`client.py`**: Uses `HttpRemoteAgent` to proxy calls to the worker. It demonstrates how state (the `Store`) is synchronized back to the client after remote execution.

## How to Run

1.  **Open two terminals.**
2.  In the **first terminal**, start the worker:
    ```bash
    PYTHONPATH=../../src:./ python3 worker.py
    ```
3.  In the **second terminal**, run the client:
    ```bash
    PYTHONPATH=../../src:./ python3 client.py
    ```

## What to Observe

- The client sends a calculation request to the worker.
- The worker executes the `CalculatorAgent`.
- The worker updates its local copy of the `Store` (setting `last_result`).
- The worker returns the result and the updated context to the client.
- The client proxy updates its local context, and you can see the `last_result` value updated in the client's store.
