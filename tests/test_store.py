import pytest
from agentswarm.datamodels import LocalStore


def test_local_store_basic_operations():
    """Test set, get, has, and len in LocalStore."""
    store = LocalStore()

    assert len(store) == 0
    assert not store.has("key1")

    store.set("key1", "value1")
    assert store.has("key1")
    assert store.get("key1") == "value1"
    assert len(store) == 1

    # Update
    store.set("key1", "value2")
    assert store.get("key1") == "value2"
    assert len(store) == 1


def test_local_store_get_nonexistent():
    """Verify that getting a nonexistent key raises KeyError or similar."""
    store = LocalStore()
    with pytest.raises(KeyError):
        store.get("missing")


def test_local_store_items():
    """Verify items() returns a copy of the internal dict."""
    store = LocalStore()
    store.set("a", 1)

    it = store.items()
    assert it == {"a": 1}

    # Modifying it should not affect the store
    it["b"] = 2
    assert not store.has("b")
