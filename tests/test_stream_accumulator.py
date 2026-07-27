"""Tests for StreamAccumulator — pure sync, no async needed."""

import pytest

from haxjobs.model.profiles import DEEPSEEK_PROFILE, DEFAULT_PROFILE, ProviderProfile
from haxjobs.model.streaming import StreamAccumulator
from haxjobs.model.types import ModelStreamEventType


@pytest.fixture
def deepseek_accumulator():
    acc = StreamAccumulator(profile=DEEPSEEK_PROFILE)
    acc.set_model_info("deepseek-v4-flash", "deepseek")
    return acc


@pytest.fixture
def default_accumulator():
    acc = StreamAccumulator(profile=DEFAULT_PROFILE)
    acc.set_model_info("test-model", "test-provider")
    return acc


class TestStreamAccumulatorBasic:
    def test_feed_text_returns_text_delta(self, deepseek_accumulator):
        event = deepseek_accumulator.feed_text("hello")
        assert event.event_type == ModelStreamEventType.TEXT_DELTA
        assert event.delta == "hello"
        assert deepseek_accumulator.accumulated_text == "hello"

    def test_multiple_text_deltas_accumulate(self, deepseek_accumulator):
        deepseek_accumulator.feed_text("hello ")
        deepseek_accumulator.feed_text("world")
        assert deepseek_accumulator.accumulated_text == "hello world"

    def test_finish_reason_defaults_to_stop(self, deepseek_accumulator):
        assert deepseek_accumulator.finish_reason == "stop"
        deepseek_accumulator.feed_finish("tool_calls")
        assert deepseek_accumulator.finish_reason == "tool_calls"

    def test_done_event_includes_finish_reason(self, deepseek_accumulator):
        deepseek_accumulator.feed_finish("stop")
        event = deepseek_accumulator.done_event(usage=None)
        assert event.event_type == ModelStreamEventType.RESPONSE_COMPLETED
        assert event.finish_reason == "stop"

    def test_failed_event(self, deepseek_accumulator):
        event = deepseek_accumulator.failed_event("bad gateway", "provider_error")
        assert event.event_type == ModelStreamEventType.RESPONSE_FAILED
        assert event.error == "bad gateway"
        assert event.category == "provider_error"


class TestStreamAccumulatorReasoning:
    def test_deepseek_profile_accepts_reasoning(self, deepseek_accumulator):
        event = deepseek_accumulator.feed_reasoning("thinking...")
        assert event is not None
        assert event.event_type == ModelStreamEventType.THINKING_DELTA
        assert event.delta == "thinking..."
        assert deepseek_accumulator.accumulated_reasoning == "thinking..."

    def test_disabled_profile_ignores_reasoning(self, default_accumulator):
        event = default_accumulator.feed_reasoning("thinking...")
        assert event is None
        assert default_accumulator.accumulated_reasoning == ""


class TestStreamAccumulatorToolCalls:
    def test_feed_tool_call_delta_accumulates(self, deepseek_accumulator):
        deepseek_accumulator.feed_tool_call_delta(0, "call_1", "my_tool", '{"key":')
        deepseek_accumulator.feed_tool_call_delta(0, None, None, '"val"}')

        assert deepseek_accumulator.has_tool_calls
        events = deepseek_accumulator.complete_tool_calls(unsafe=False)
        assert len(events) == 1
        assert events[0].call_id == "call_1"
        assert events[0].tool_name == "my_tool"
        assert events[0].arguments == '{"key":"val"}'
        assert events[0].tool_calls_unsafe is False
        assert not deepseek_accumulator.has_tool_calls

    def test_feed_tool_call_without_id_not_emitted(self, deepseek_accumulator):
        deepseek_accumulator.feed_tool_call_delta(0, "incomplete_call", "tool", "")
        assert not deepseek_accumulator.has_tool_calls

    def test_unsafe_tool_call_marked(self, deepseek_accumulator):
        deepseek_accumulator.feed_tool_call_delta(0, "call_1", "my_tool", '{"key":"val"}')
        events = deepseek_accumulator.complete_tool_calls(unsafe=True)
        assert events[0].tool_calls_unsafe is True

    def test_multiple_tool_calls(self, deepseek_accumulator):
        deepseek_accumulator.feed_tool_call_delta(0, "call_a", "tool_a", '{}')
        deepseek_accumulator.feed_tool_call_delta(1, "call_b", "tool_b", '{}')
        events = deepseek_accumulator.complete_tool_calls(unsafe=False)
        assert len(events) == 2
        assert {e.call_id for e in events} == {"call_a", "call_b"}

    def test_complete_tool_calls_clears_state(self, deepseek_accumulator):
        deepseek_accumulator.feed_tool_call_delta(0, "call_1", "tool", '{}')
        deepseek_accumulator.complete_tool_calls(unsafe=False)
        assert not deepseek_accumulator.has_tool_calls
