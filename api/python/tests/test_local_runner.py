import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_RUNNER_PATH = REPO_ROOT / "lambdas" / "local_runner.py"


def _load_local_runner():
    spec = importlib.util.spec_from_file_location("quilt_local_runner", LOCAL_RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invoke_handler_uses_unbound_class_handler():
    local_runner = _load_local_runner()
    event = {"request": "value"}
    calls = {}

    def lambda_handler(lambda_event, lambda_context):
        calls["args"] = (lambda_event, lambda_context)
        return {"ok": True}

    class DummyHandler:
        handler = lambda_handler

    with pytest.raises(TypeError, match="3 were given"):
        DummyHandler().handler(event, None)

    assert local_runner._invoke_handler(DummyHandler.handler, event, None) == {"ok": True}
    assert calls["args"] == (event, None)


def test_invoke_handler_awaits_async_handler():
    local_runner = _load_local_runner()
    event = {"request": "value"}

    async def lambda_handler(lambda_event, lambda_context):
        return {"event": lambda_event, "context": lambda_context}

    assert local_runner._invoke_handler(lambda_handler, event, None) == {
        "event": event,
        "context": None,
    }
