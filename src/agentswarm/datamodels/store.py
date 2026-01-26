from abc import ABC, abstractmethod


class Store(ABC):
    """
    The Store class defines a simple key/value API to access the store.
    The implementation can vary from a local dictionary, to a distributed remote store.
    """

    @abstractmethod
    def get(self, key: str) -> any:
        """
        Obtains the value associated with the given key.
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: any):
        """
        Sets the value associated with the given key.
        """
        raise NotImplementedError

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Checks if the store has a value associated with the given key.
        """
        raise NotImplementedError

    @abstractmethod
    def items(self) -> dict[str, any]:
        """
        Returns all key-value pairs in the store.
        (Primary used for nice tracing)
        """
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Returns the configuration needed to recreate the store.
        WARNING: Never share keys or other secret during this process.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def recreate(cls, config: dict) -> "Store":
        """
        Recreates a Store instance from a configuration dictionary.
        """
        raise NotImplementedError
