# Store

The `Store` is a fundamental abstraction in Agentswarm that decouples state persistence from agent logic. It allows agents to share data (like task results, intermediate variables, or long-term memory) without knowing *how* or *where* that data is stored.

## The Abstract Concept

The `Store` class defines a simple key-value interface. By designing your agents to rely on this interface, you make them portable and adaptable to different environments.

- **Abstraction**: Your agent simply calls `store.set("key", value)` or `store.get("key")`.
- **Flexibility**: In a local script, this might just write to a Python dictionary. In a production cloud deployment, the underlying implementation could speak to Redis, a SQL database, or a cloud bucket.

::: agentswarm.datamodels.Store

## Custom Implementations

You are encouraged to create your own Store implementations for your specific needs. For example, if you need persistence across reboots, you might implement a `FileStore` or a `RedisStore`.

### Example: Creating a Redis Store

```python
from agentswarm.datamodels import Store
import redis

class RedisStore(Store):
    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db)

    def get(self, key: str) -> any:
        return self.r.get(key)

    def set(self, key: str, value: any):
        self.r.set(key, value)

    def has(self, key: str) -> bool:
        return self.r.exists(key)
    
    def items(self) -> dict:
        # Implementation to fetch all keys...
        pass
```

## Local Store

The library comes with a ready-to-use `LocalStore` which implements the interface using an in-memory dictionary. This is perfect for testing, scripts, and single-instance applications where persistence is not required.

::: agentswarm.datamodels.LocalStore
