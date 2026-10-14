"""
Turns a raw Observation (+ RAG context) into a structured security
explanation via the LLM, using LLMProvider.generate_structured().

This does NOT decide whether something is a "confirmed" vulnerability
— it produces a `potential` Finding. Confirmation (Phase 4's Security
Agent, with controlled verification tests) comes later.
"""
import logging
from typing import Any

from app.services.llm import get_llm_provider

logger = logging.getLogger(__name__)


_SCHEMA_HINT = """{
  "title": "short human-readable finding title",
  "category": "e.g. SQL Injection, XSS, Broken Access Control, Security Misconfiguration",
  "severity": "informational | low | medium | high | critical",
  "confidence": 0.0,
  "description": "1-3 sentences describing what was observed and why it's concerning",
  "impact": "1-2 sentences on what an attacker could achieve",
  "cwe_id": "e.g. CWE-89, or null if unknown",
  "owasp_category": "e.g. A03:2021 - Injection, or null if unknown",
  "remediation": "concrete, actionable fix guidance",
  "reasoning": "1-2 sentences on how the evidence and security knowledge support this conclusion"
}"""

_SYSTEM_PROMPT = (
    "You are a security analysis assistant inside CodeShieldAI, an evidence-driven "
    "security platform. You are given a raw observation — either from static analysis "
    "(Semgrep/Bandit, against source code) or a controlled dynamic check (against a live "
    "authorized web target) — plus retrieved security knowledge (OWASP/CWE context). "
    "Your job is to explain the finding clearly and accurately, grounded ONLY in the "
    "observation and the provided knowledge context. Do not invent evidence that wasn't "
    "given to you. If the observation is likely a false positive or too ambiguous to "
    "assess, say so plainly in the reasoning field and lower the confidence score "
    "accordingly. Never claim certainty (confidence 1.0) from a single observation alone."
)


_REQUIRED_FIELDS = {
    "title",
    "category",
    "severity",
    "confidence",
    "description",
    "impact",
    "cwe_id",
    "owasp_category",
    "remediation",
    "reasoning",
}

_ALLOWED_SEVERITIES = {
    "informational", "low", "medium", "high", "critical"
}


def _is_valid_finding(result: dict[str, Any]) -> bool:
    """Check the required structure and basic value constraints."""
    if not _REQUIRED_FIELDS.issubset(result):
        return False

    if not all(isinstance(result[field], str) and result[field].strip()
               for field in (
                   "title", "category", "description", "impact",
                   "remediation", "reasoning"
               )):
        return False

    if result["severity"] not in _ALLOWED_SEVERITIES:
        return False

    confidence = result["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0.0 <= confidence <= 1.0
    ):
        return False

    for field in ("cwe_id", "owasp_category"):
        if result[field] is not None and not isinstance(result[field], str):
            return False

    return True


def explain_observation(
    *,
    source: str,
    rule_id: str | None,
    message: str,
    file: str | None = None,
    line: int | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    parameter: str | None = None,
    code_snippet: str | None,
    raw_severity: str | None,
    language: str | None,
    rag_context: list[dict[str, Any]],
) -> dict[str, Any]:
    context_block = "\n\n".join(
        f"[{c.get('title')} | {c.get('cwe') or 'n/a'} | {c.get('owasp') or 'n/a'}]\n{c.get('text')}"
        for c in rag_context
    ) or "(no relevant security knowledge retrieved)"

    if source == "dynamic":
        location_block = (
            f"HTTP method: {http_method or 'GET'}\n"
            f"Endpoint: {endpoint or 'unknown'}\n"
            f"Parameter: {parameter or 'n/a'}"
        )
    else:
        location_block = f"File: {file or 'unknown'}\nLine: {line or 'unknown'}"

    prompt = f"""Observation source: {source}
Rule ID: {rule_id or 'n/a'}
Language: {language or 'unknown'}
{location_block}
Tool-reported severity: {raw_severity or 'unknown'}

Observation message:
{message}

Code/response context (if available):
{code_snippet or '(not available)'}

Retrieved security knowledge:
{context_block}

Produce the structured JSON finding now."""


    try:
        provider = get_llm_provider()
        result = provider.generate_structured(
            prompt,
            schema_hint=_SCHEMA_HINT,
            system_prompt=_SYSTEM_PROMPT,
        )
    except Exception as exc:
        logger.warning(
            "LLM structured explanation failed for %s (%s)",
            endpoint or file,
            type(exc).__name__,
        )
        return _fallback_finding(source, rule_id, message, raw_severity)

    if (
        not isinstance(result, dict)
        or "error" in result
        or not _is_valid_finding(result)
    ):
        logger.warning(
            "LLM returned an invalid structured finding for %s",
            endpoint or file,
        )
        return _fallback_finding(source, rule_id, message, raw_severity)

    return result




def _fallback_finding(source: str, rule_id: str | None, message: str, raw_severity: str | None) -> dict[str, Any]:
    """Used when the LLM call fails or returns invalid JSON — the scan
    must still produce a usable (if less polished) finding rather than
    silently dropping the observation."""
    return {
        "title": f"{source} finding: {rule_id or 'unspecified rule'}",
        "category": "Uncategorized",
        "severity": (raw_severity or "medium").lower() if (raw_severity or "").lower() in
                    {"informational", "low", "medium", "high", "critical"} else "medium",
        "confidence": 0.3,
        "description": message,
        "impact": "Impact not assessed — LLM explanation unavailable for this observation.",
        "cwe_id": None,
        "owasp_category": None,
        "remediation": "Review this finding manually; automated explanation was unavailable.",
        "reasoning": "Fallback: the LLM call failed or returned an unparsable response.",
    }
