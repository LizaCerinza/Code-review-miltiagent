import json

import pytest

from reviewer.agents.base import REPORT_SCHEMA, AgentError, parse_report
from reviewer.llm import LLMResponse
from reviewer.models import Usage

VALID = {
    "summary": "Un problema",
    "findings": [
        {
            "file": "src/users.controller.ts", "line": 42, "severity": "critical",
            "confidence": "high", "category": "broken-access-control", "title": "Sin guard",
            "message": "El endpoint no valida al usuario.", "evidence": "@Delete(':id')",
            "suggestion": "Agregar el guard.",
        }
    ],
}


def response(text):
    return LLMResponse(text=text, model="gpt-4.1-mini",
                       usage=Usage(input_tokens=1200, output_tokens=300))


def test_parse_valid_report():
    report = parse_report("security", response(json.dumps(VALID)))
    assert report.agent == "security"
    assert report.summary == "Un problema"
    assert report.findings[0].agents == ["security"]
    assert report.findings[0].severity.value == "critical"
    assert report.usage.input_tokens == 1200
    assert report.model == "gpt-4.1-mini"


@pytest.mark.parametrize("text", ["{no es json", '{"summary": "x", "findings": [{"file": 1}]}'])
def test_parse_invalid_output(text):
    with pytest.raises(AgentError, match="salida inválida"):
        parse_report("design", response(text))


def test_schema_is_strict():
    item = REPORT_SCHEMA["properties"]["findings"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"])
    assert REPORT_SCHEMA["additionalProperties"] is False
