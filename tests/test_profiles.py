"""Tests for ProviderProfile detection."""

from haxjobs.model.profiles import (
    DEEPSEEK_PROFILE,
    DEFAULT_PROFILE,
    OPENAI_PROFILE,
    detect_profile,
)


class TestDetectProfile:
    def test_detect_deepseek_by_provider_name(self):
        profile = detect_profile("deepseek", "https://api.deepseek.com/v1")
        assert profile is DEEPSEEK_PROFILE

    def test_detect_deepseek_by_base_url(self):
        profile = detect_profile("unknown", "https://api.deepseek.com/v1/chat")
        assert profile is DEEPSEEK_PROFILE

    def test_detect_openai_by_provider_name(self):
        profile = detect_profile("openai", "https://api.openai.com/v1")
        assert profile is OPENAI_PROFILE

    def test_detect_openai_by_base_url(self):
        profile = detect_profile("unknown", "https://api.openai.com/v1")
        assert profile is OPENAI_PROFILE

    def test_unknown_provider_returns_default(self):
        profile = detect_profile("groq", "https://api.groq.com/v1")
        assert profile is DEFAULT_PROFILE

    def test_deepseek_profile_has_reasoning_preservation(self):
        assert DEEPSEEK_PROFILE.requires_reasoning_preservation is True
        assert DEEPSEEK_PROFILE.thinking_format == "deepseek"

    def test_default_profile_disables_reasoning(self):
        assert DEFAULT_PROFILE.thinking_format == "disabled"
        assert DEFAULT_PROFILE.reasoning_effort_field is None
        assert DEFAULT_PROFILE.supports_json_mode is False

    def test_provider_profile_is_immutable(self):
        """ProviderProfile is frozen — can't mutate flags."""
        import pytest
        with pytest.raises(Exception):  # dataclass FrozenInstanceError or similar
            DEEPSEEK_PROFILE.thinking_format = "disabled"  # type: ignore[misc]
