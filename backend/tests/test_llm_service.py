from unittest.mock import MagicMock, patch
import pytest
from app.services.llm_service import LLMService, redact_sensitive


@pytest.mark.asyncio
async def test_offline_deterministic_synthesizer():
    service = LLMService()
    service.api_key = ""

    chunks = [
        {"text": "First chunk provides grounding context for the question.", "document_name": "doc1.md"},
        {"text": "Second chunk explains the scoring formula.", "document_name": "doc2.md"},
    ]

    res = await service.generate_response("Explain the system", context_chunks=chunks)
    assert res["provider"] == "deterministic-offline"
    assert res["advisory"] is True
    assert "[1]" in res["answer"]


@pytest.mark.asyncio
async def test_openai_adapter_mocked():
    service = LLMService()
    synthetic_key = "test_key_" + "0" * 20
    service.api_key = synthetic_key
    service.provider = "openai-compatible"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Answer with citation [1]."}}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await service.generate_response("Question?")
        assert res["answer"] == "Answer with citation [1]."
        assert res["provider"] == "openai-compatible"


@pytest.mark.asyncio
async def test_anthropic_adapter_mocked():
    service = LLMService()
    synthetic_key = "test_key_" + "0" * 20
    service.api_key = synthetic_key
    service.provider = "anthropic"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"text": "Anthropic grounded answer [1]."}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await service.generate_response("Question?")
        assert res["answer"] == "Anthropic grounded answer [1]."
        assert res["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_gemini_adapter_mocked():
    service = LLMService()
    synthetic_key = "test_key_" + "0" * 20
    service.api_key = synthetic_key
    service.provider = "gemini"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Gemini answer [1]."}]}}]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await service.generate_response("Question?")
        assert res["answer"] == "Gemini answer [1]."
        assert res["provider"] == "gemini"


def test_error_redaction_runtime_synthetic():
    synthetic_bearer = "Bearer " + "test_tok_" + ("a" * 24)
    raw_error = f"Failed request with header {synthetic_bearer} and key=param_12345"
    redacted = redact_sensitive(raw_error)

    assert "test_tok_" not in redacted
    assert "[REDACTED]" in redacted
