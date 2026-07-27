"""ProviderProfile — pure-data flags describing a provider's behaviour.

The adapter reads these flags. It never branches on provider name.
Adding a new provider means one new constant. Zero code changes elsewhere.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderProfile:
    """Pure-data flags describing a provider's behaviour.

    The adapter reads these flags. It never branches on provider name.
    Adding a new provider means one new constant. Zero code changes elsewhere.
    """

    thinking_format: str  # "disabled" | "deepseek" | "anthropic"
    max_tokens_field: str  # "max_tokens" | "max_completion_tokens"
    extra_body: dict = field(default_factory=dict)  # e.g. {"thinking": {"type": "enabled"}}
    reasoning_effort_field: str | None = None  # "reasoning_effort" or None
    requires_reasoning_preservation: bool = False  # carry reasoning_content across tool turns
    supports_stream_options: bool = True
    supports_json_mode: bool = False


# ── Provider constants ──

DEEPSEEK_PROFILE = ProviderProfile(
    thinking_format="deepseek",
    max_tokens_field="max_tokens",
    extra_body={"thinking": {"type": "enabled"}},
    reasoning_effort_field="reasoning_effort",
    requires_reasoning_preservation=True,
    supports_stream_options=True,
    supports_json_mode=True,
)

OPENAI_PROFILE = ProviderProfile(
    thinking_format="disabled",
    max_tokens_field="max_completion_tokens",
    extra_body={},
    reasoning_effort_field="reasoning_effort",
    requires_reasoning_preservation=False,
    supports_stream_options=True,
    supports_json_mode=True,
)

DEFAULT_PROFILE = ProviderProfile(
    thinking_format="disabled",
    max_tokens_field="max_completion_tokens",
    extra_body={},
    reasoning_effort_field=None,
    requires_reasoning_preservation=False,
    supports_stream_options=True,
    supports_json_mode=False,
)


def detect_profile(provider: str, base_url: str) -> ProviderProfile:
    """Auto-detect profile from provider name and base URL.

    Falls back to DEFAULT_PROFILE if unknown. Users can override by passing
    an explicit profile when constructing the adapter.
    """
    if provider == "deepseek" or "deepseek.com" in base_url:
        return DEEPSEEK_PROFILE
    if provider == "openai" or "api.openai.com" in base_url:
        return OPENAI_PROFILE
    return DEFAULT_PROFILE
