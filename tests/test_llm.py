import json
from types import SimpleNamespace

import httpx2
import openai
import pytest

from reviewer.agents.base import REPORT_SCHEMA
from reviewer.config import ReviewConfig
from reviewer.llm import (
    LLMError,
    create_provider,
    missing_credentials,
    normalize_azure_endpoint,
)
from reviewer.llm.anthropic import FALLBACK_BETA, AnthropicProvider
from reviewer.llm.azure import AzureOpenAIProvider

CONFIG = ReviewConfig()
ENDPOINT = "https://mi-recurso.openai.azure.com"


def call(provider, model="gpt-4.1-mini", config=CONFIG):
    return provider.complete_json(system="S", user="U", schema=REPORT_SCHEMA, model=model,
                                  config=config)


# ---- Azure OpenAI -------------------------------------------------------------

def completion(content='{"summary": "ok", "findings": []}', finish="stop", refusal=None):
    return {
        "id": "x", "object": "chat.completion", "created": 0, "model": "gpt-4.1-mini",
        "choices": [{"index": 0, "finish_reason": finish,
                     "message": {"role": "assistant", "content": content, "refusal": refusal}}],
        "usage": {"prompt_tokens": 1500, "completion_tokens": 200, "total_tokens": 1700},
    }


def azure(handler):
    client = openai.AsyncAzureOpenAI(
        azure_endpoint=ENDPOINT, api_key="clave", api_version="2024-10-21", max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )
    return AzureOpenAIProvider(client=client)


async def test_azure_sends_structured_request_to_deployment():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["api_key"] = request.headers.get("api-key")
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json=completion())

    response = await call(azure(handler))

    assert "/openai/deployments/gpt-4.1-mini/chat/completions" in seen["url"]
    assert "api-version=2024-10-21" in seen["url"]
    assert seen["api_key"] == "clave"
    body = seen["body"]
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == REPORT_SCHEMA
    assert body["temperature"] == 0.1
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert response.text == '{"summary": "ok", "findings": []}'
    assert response.usage.input_tokens == 1500 and response.usage.output_tokens == 200


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (completion(finish="content_filter", content=None), "filtro de contenido"),
        (completion(finish="length"), "max_tokens"),
        (completion(content=None, refusal="no puedo"), "declinó"),
        (completion(content=""), "no tiene texto"),
    ],
)
async def test_azure_errors(payload, message):
    with pytest.raises(LLMError, match=message):
        await call(azure(lambda request: httpx2.Response(200, json=payload)))


async def test_azure_prompt_blocked_by_content_filter():
    error = {"error": {"code": "content_filter", "message": "filtered", "status": 400}}
    with pytest.raises(LLMError, match="filtro de contenido"):
        await call(azure(lambda request: httpx2.Response(400, json=error)))


def recording_azure(seen):
    def handler(request):
        seen.append((str(request.url), json.loads(request.content)))
        return httpx2.Response(200, json=completion())

    return AzureOpenAIProvider(
        endpoint=ENDPOINT, api_key="clave", api_version="2024-10-21",
        reasoning_api_version="2025-04-01-preview",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )


async def test_azure_reasoning_model_uses_its_own_parameters_and_api_version():
    seen = []
    provider = recording_azure(seen)

    await call(provider, model="gpt-5-mini")
    await call(provider, model="gpt-4.1-mini")

    (reasoning_url, reasoning), (classic_url, classic) = seen
    assert "/deployments/gpt-5-mini/" in reasoning_url
    assert "api-version=2025-04-01-preview" in reasoning_url
    assert reasoning["max_completion_tokens"] == CONFIG.max_tokens
    assert reasoning["reasoning_effort"] == "medium"
    assert "temperature" not in reasoning and "max_tokens" not in reasoning
    assert "api-version=2024-10-21" in classic_url
    assert classic["temperature"] == 0.1 and classic["max_tokens"] == CONFIG.max_tokens
    assert "reasoning_effort" not in classic


async def test_reasoning_model_declared_by_name():
    seen = []
    config = ReviewConfig(azure_reasoning_models=("revisor-razonamiento",),
                          azure_reasoning_effort="high")
    await call(recording_azure(seen), model="revisor-razonamiento", config=config)
    assert seen[0][1]["reasoning_effort"] == "high"


@pytest.mark.parametrize(
    ("model", "expected"),
    [("gpt-5-mini", True), ("GPT-5", True), ("o4-mini", True), ("o3", True),
     ("gpt-4.1-mini", False), ("gpt-4o", False)],
)
def test_is_azure_reasoning(model, expected):
    assert ReviewConfig().is_azure_reasoning(model) is expected


# ---- Anthropic -----------------------------------------------------------------

class FakeStream:
    def __init__(self, calls, message, **kwargs):
        calls.append(kwargs)
        self.message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_final_message(self):
        return self.message


def anthropic_provider(calls, stop_reason="end_turn", text='{"summary": "", "findings": []}'):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    message = SimpleNamespace(stop_reason=stop_reason, model="claude-opus-5-5", content=content,
                              usage=SimpleNamespace(input_tokens=10, output_tokens=5))
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
        stream=lambda **kw: FakeStream(calls, message, **kw))))
    return AnthropicProvider(client=client)


async def test_anthropic_sends_expected_request():
    calls = []
    config = ReviewConfig(provider="anthropic", effort="xhigh")
    response = await call(anthropic_provider(calls), model="claude-opus-5-5", config=config)

    sent = calls[0]
    assert sent["model"] == "claude-opus-5-5"
    assert sent["betas"] == [FALLBACK_BETA]
    assert sent["fallbacks"] == "default"
    assert sent["output_config"]["effort"] == "xhigh"
    assert sent["output_config"]["format"] == {"type": "json_schema", "schema": REPORT_SCHEMA}
    assert response.usage.input_tokens == 10


@pytest.mark.parametrize(
    ("stop_reason", "text", "message"),
    [("refusal", None, "declinó"), ("max_tokens", "{", "max_tokens"), ("end_turn", None, "texto")],
)
async def test_anthropic_errors(stop_reason, text, message):
    with pytest.raises(LLMError, match=message):
        await call(anthropic_provider([], stop_reason, text), model="claude-opus-5-5")


# ---- Selección de proveedor y credenciales ------------------------------------

def test_missing_credentials_per_provider():
    assert missing_credentials("azure", {}) == ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
    assert missing_credentials("azure", {"AZURE_OPENAI_API_KEY": "k"}) == ["AZURE_OPENAI_ENDPOINT"]
    env = {"AZURE_OPENAI_API_KEY": "k", "AZURE_OPENAI_ENDPOINT": ENDPOINT}
    assert missing_credentials("azure", env) == []
    assert missing_credentials("anthropic", env) == ["ANTHROPIC_API_KEY"]
    assert missing_credentials("anthropic", {"ANTHROPIC_AUTH_TOKEN": "t"}) == []


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://topicos-avanzados.openai.azure.com/",
        "https://topicos-avanzados.openai.azure.com",
        "https://topicos-avanzados.openai.azure.com/openai/v1/",
        "  https://topicos-avanzados.openai.azure.com/openai/  ",
    ],
)
def test_normalize_azure_endpoint(endpoint):
    assert normalize_azure_endpoint(endpoint) == "https://topicos-avanzados.openai.azure.com/"


def test_create_provider():
    env = {"AZURE_OPENAI_API_KEY": "k", "AZURE_OPENAI_ENDPOINT": ENDPOINT}
    assert isinstance(create_provider(ReviewConfig(), env), AzureOpenAIProvider)
    assert isinstance(create_provider(ReviewConfig(provider="anthropic"),
                                      {"ANTHROPIC_API_KEY": "k"}), AnthropicProvider)
