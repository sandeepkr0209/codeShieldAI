from unittest.mock import MagicMock, patch

from app.services.llm.security_explainer import explain_observation


def test_explain_observation_returns_llm_structured_result():
    fake_provider = MagicMock()
    fake_provider.generate_structured.return_value = {
        "title": "SQL Injection in db.py",
        "category": "SQL Injection",
        "severity": "high",
        "confidence": 0.8,
        "description": "User input reaches a SQL query without parameterization.",
        "impact": "An attacker could read or modify database contents.",
        "cwe_id": "CWE-89",
        "owasp_category": "A03:2021 - Injection",
        "remediation": "Use parameterized queries.",
        "reasoning": "Observation matches known SQLi pattern; RAG context confirms CWE-89.",
    }

    with patch("app.services.llm.security_explainer.get_llm_provider", return_value=fake_provider):
        result = explain_observation(
            source="semgrep",
            rule_id="python.sql-injection",
            message="Possible SQL injection",
            file="db.py",
            line=42,
            code_snippet="cursor.execute(query)",
            raw_severity="ERROR",
            language="python",
            rag_context=[{"title": "SQL Injection", "cwe": "CWE-89", "owasp": "A03", "text": "..."}],
        )

    assert result["title"] == "SQL Injection in db.py"
    assert result["cwe_id"] == "CWE-89"
    fake_provider.generate_structured.assert_called_once()


def test_explain_observation_falls_back_on_llm_failure():
    fake_provider = MagicMock()
    fake_provider.generate_structured.return_value = {"error": "invalid_json", "raw_response": "not json"}

    with patch("app.services.llm.security_explainer.get_llm_provider", return_value=fake_provider):
        result = explain_observation(
            source="bandit",
            rule_id="B608",
            message="Possible SQL injection via string formatting",
            file="db.py",
            line=10,
            code_snippet=None,
            raw_severity="MEDIUM",
            language="python",
            rag_context=[],
        )

    assert result["confidence"] == 0.3
    assert "Fallback" in result["reasoning"]
    assert result["category"] == "Uncategorized"


def test_explain_observation_falls_back_on_missing_required_field():
    fake_provider = MagicMock()
    fake_provider.generate_structured.return_value = {
        "title": "SQL Injection",
        "severity": "high",
        "confidence": 0.8,
    }

    with patch(
        "app.services.llm.security_explainer.get_llm_provider",
        return_value=fake_provider,
    ):
        result = explain_observation(
            source="semgrep",
            rule_id="python.sql-injection",
            message="Possible SQL injection",
            file="db.py",
            code_snippet=None,
            raw_severity="HIGH",
            language="python",
            rag_context=[],
        )

    assert result["confidence"] == 0.3
    assert result["category"] == "Uncategorized"


def test_explain_observation_falls_back_on_invalid_confidence():
    fake_provider = MagicMock()
    fake_provider.generate_structured.return_value = {
        "title": "SQL Injection",
        "category": "SQL Injection",
        "severity": "high",
        "confidence": 1.5,
        "description": "Potential SQL injection.",
        "impact": "Database data could be exposed.",
        "cwe_id": "CWE-89",
        "owasp_category": "A03:2021 - Injection",
        "remediation": "Use parameterized queries.",
        "reasoning": "The observation suggests a possible injection issue.",
    }

    with patch(
        "app.services.llm.security_explainer.get_llm_provider",
        return_value=fake_provider,
    ):
        result = explain_observation(
            source="semgrep",
            rule_id="python.sql-injection",
            message="Possible SQL injection",
            file="db.py",
            code_snippet=None,
            raw_severity="HIGH",
            language="python",
            rag_context=[],
        )

    assert result["confidence"] == 0.3
    assert result["category"] == "Uncategorized"


def test_explain_observation_falls_back_on_provider_exception():
    fake_provider = MagicMock()
    fake_provider.generate_structured.side_effect = RuntimeError(
        "Provider unavailable"
    )

    with patch(
        "app.services.llm.security_explainer.get_llm_provider",
        return_value=fake_provider,
    ):
        result = explain_observation(
            source="semgrep",
            rule_id="python.sql-injection",
            message="Possible SQL injection",
            file="db.py",
            code_snippet=None,
            raw_severity="HIGH",
            language="python",
            rag_context=[],
        )

    assert result["confidence"] == 0.3
    assert result["category"] == "Uncategorized"