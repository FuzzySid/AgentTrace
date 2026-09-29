"""Provider-agnostic model wrapper with GenAI semantic-convention attributes."""

import json
from typing import Any

from litellm import completion
from opentelemetry import trace

from app.config.models import API_BASE, API_KEY, PROVIDER_NAME, model_for_tier
from app.instrumentation.setup import current_capture_tier

tracer = trace.get_tracer("agenttrace.llm")


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(_field(part, "text", "")) for part in value)
    return ""


def chat(messages: list[dict[str, str]], *, tier: str, purpose: str) -> str:
    """Make one non-streaming chat request and record provider-returned model/usage."""
    model = model_for_tier(tier)
    with tracer.start_as_current_span(f"gen_ai.chat {purpose}") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", PROVIDER_NAME)
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("agenttrace.llm.purpose", purpose)
        if current_capture_tier() == "full":
            span.set_attribute("gen_ai.input.messages", json.dumps(messages, ensure_ascii=False))

        kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.1, "stream": False}
        if API_KEY:
            kwargs["api_key"] = API_KEY
        if API_BASE:
            kwargs["api_base"] = API_BASE
        response = completion(**kwargs)

        served_model = _field(response, "model")
        if served_model:
            span.set_attribute("gen_ai.response.model", str(served_model))
        response_id = _field(response, "id")
        if response_id:
            span.set_attribute("gen_ai.response.id", str(response_id))
        usage = _field(response, "usage")
        input_tokens = _field(usage, "prompt_tokens", _field(usage, "input_tokens"))
        output_tokens = _field(usage, "completion_tokens", _field(usage, "output_tokens"))
        if isinstance(input_tokens, int):
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        if isinstance(output_tokens, int):
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
        choices = _field(response, "choices", []) or []
        if not choices:
            raise RuntimeError("The model response contained no choices")
        choice = choices[0]
        finish_reason = _field(choice, "finish_reason")
        if finish_reason:
            span.set_attribute("gen_ai.response.finish_reasons", [str(finish_reason)])
        message = _field(choice, "message", {})
        content = _message_text(_field(message, "content", ""))
        if current_capture_tier() == "full":
            span.set_attribute(
                "gen_ai.output.messages",
                json.dumps([{"role": "assistant", "content": content}], ensure_ascii=False),
            )
        return content
