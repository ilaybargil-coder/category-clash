import sys
from types import SimpleNamespace

from app import report_judge


async def test_judge_is_disabled_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(report_judge.settings, "anthropic_api_key", "")

    assert await report_judge.judge_report("קטגוריה", "מועמד") is None


async def test_judge_uses_strict_anthropic_call_without_network(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeMessages:
        async def create(self, **kwargs):
            calls["message"] = kwargs
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="accept")])

    class FakeAsyncAnthropic:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.messages = FakeMessages()

    monkeypatch.setitem(
        sys.modules,
        "anthropic",
        SimpleNamespace(AsyncAnthropic=FakeAsyncAnthropic),
    )
    monkeypatch.setattr(report_judge.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(report_judge.settings, "report_judge_model", "test-model")

    verdict = await report_judge.judge_report("קטגוריה", "מועמד")

    assert verdict == "accept"
    assert calls["client"] == {"api_key": "test-key", "timeout": 6.0}
    message = calls["message"]
    assert isinstance(message, dict)
    assert message["model"] == "test-model"
    assert message["max_tokens"] == 5
    assert message["temperature"] == 0
    assert "accept, reject, or uncertain" in message["system"]
