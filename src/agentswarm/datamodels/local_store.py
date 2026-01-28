from .store import Store


class LocalStore(Store):
    """
    The LocalStore class implements a simple key-value store in memory.
    """

    def __init__(self):
        self.store = {}

    def get(self, key: str) -> any:
        return self.store[key]

    def set(self, key: str, value: any):
        self.store[key] = value

    def has(self, key: str) -> bool:
        return key in self.store

    def items(self) -> dict[str, any]:
        return self.store.copy()

    def __len__(self) -> int:
        return len(self.store)

    def to_dict(self) -> dict:
        from ..utils.exceptions import RemoteExecutionNotSupportedError

        raise RemoteExecutionNotSupportedError(
            "LocalStore cannot be serialized for remote execution."
        )

    @classmethod
    def recreate(cls, config: dict) -> "LocalStore":
        from ..utils.exceptions import RemoteExecutionNotSupportedError

        raise RemoteExecutionNotSupportedError(
            "LocalStore cannot be recreated from remote configuration."
        )
