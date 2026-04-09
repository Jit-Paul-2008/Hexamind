from __future__ import annotations

from contextvars import ContextVar, Token
from threading import Lock
from typing import Any


_ACTIVE_SESSION_ID: ContextVar[str | None] = ContextVar("hexamind_active_session_id", default=None)
_LOCK = Lock()
_SESSION_USAGE: dict[str, dict[str, Any]] = {}


def _empty_usage() -> dict[str, Any]:
    return {
        "llmPromptTokensEstimated": 0,
        "llmCompletionTokensEstimated": 0,
        "llmTotalTokensEstimated": 0,
        "llmApiCallsEquivalent": 0,
        "retrievalApiCallsEquivalent": 0,
        "totalApiCallsEquivalent": 0,
        "llmCallsByProvider": {},
        "retrievalCallsByProvider": {},
    }


def activate_session(session_id: str) -> Token:
    return _ACTIVE_SESSION_ID.set(session_id)


def deactivate_session(token: Token) -> None:
    _ACTIVE_SESSION_ID.reset(token)


def _get_or_create_usage(session_id: str) -> dict[str, Any]:
    usage = _SESSION_USAGE.get(session_id)
    if usage is None:
        usage = _empty_usage()
        _SESSION_USAGE[session_id] = usage
    return usage


def _provider_bucket(usage: dict[str, Any], bucket: str, provider: str) -> None:
    value = provider.strip() or "unknown"
    counts: dict[str, int] = usage[bucket]
    counts[value] = counts.get(value, 0) + 1


def record_llm_call(
    prompt_tokens_estimated: int,
    completion_tokens_estimated: int,
    provider: str,
) -> None:
    session_id = _ACTIVE_SESSION_ID.get()
    if not session_id:
        return

    prompt_tokens = max(0, int(prompt_tokens_estimated))
    completion_tokens = max(0, int(completion_tokens_estimated))

    with _LOCK:
        usage = _get_or_create_usage(session_id)
        usage["llmPromptTokensEstimated"] += prompt_tokens
        usage["llmCompletionTokensEstimated"] += completion_tokens
        usage["llmTotalTokensEstimated"] = (
            usage["llmPromptTokensEstimated"] + usage["llmCompletionTokensEstimated"]
        )
        usage["llmApiCallsEquivalent"] += 1
        usage["totalApiCallsEquivalent"] = (
            usage["llmApiCallsEquivalent"] + usage["retrievalApiCallsEquivalent"]
        )
        _provider_bucket(usage, "llmCallsByProvider", provider)


def record_llm_call_started(prompt_tokens_estimated: int, provider: str) -> None:
    session_id = _ACTIVE_SESSION_ID.get()
    if not session_id:
        return

    prompt_tokens = max(0, int(prompt_tokens_estimated))
    with _LOCK:
        usage = _get_or_create_usage(session_id)
        usage["llmPromptTokensEstimated"] += prompt_tokens
        usage["llmTotalTokensEstimated"] = (
            usage["llmPromptTokensEstimated"] + usage["llmCompletionTokensEstimated"]
        )
        usage["llmApiCallsEquivalent"] += 1
        usage["totalApiCallsEquivalent"] = (
            usage["llmApiCallsEquivalent"] + usage["retrievalApiCallsEquivalent"]
        )
        _provider_bucket(usage, "llmCallsByProvider", provider)


def record_llm_completion_tokens(completion_tokens_estimated: int) -> None:
    session_id = _ACTIVE_SESSION_ID.get()
    if not session_id:
        return

    completion_tokens = max(0, int(completion_tokens_estimated))
    with _LOCK:
        usage = _get_or_create_usage(session_id)
        usage["llmCompletionTokensEstimated"] += completion_tokens
        usage["llmTotalTokensEstimated"] = (
            usage["llmPromptTokensEstimated"] + usage["llmCompletionTokensEstimated"]
        )


def record_retrieval_call(provider: str) -> None:
    session_id = _ACTIVE_SESSION_ID.get()
    if not session_id:
        return

    with _LOCK:
        usage = _get_or_create_usage(session_id)
        usage["retrievalApiCallsEquivalent"] += 1
        usage["totalApiCallsEquivalent"] = (
            usage["llmApiCallsEquivalent"] + usage["retrievalApiCallsEquivalent"]
        )
        _provider_bucket(usage, "retrievalCallsByProvider", provider)


def get_session_usage(session_id: str) -> dict[str, Any]:
    with _LOCK:
        usage = _SESSION_USAGE.get(session_id)
        if usage is None:
            return _empty_usage()
        return {
            "llmPromptTokensEstimated": int(usage["llmPromptTokensEstimated"]),
            "llmCompletionTokensEstimated": int(usage["llmCompletionTokensEstimated"]),
            "llmTotalTokensEstimated": int(usage["llmTotalTokensEstimated"]),
            "llmApiCallsEquivalent": int(usage["llmApiCallsEquivalent"]),
            "retrievalApiCallsEquivalent": int(usage["retrievalApiCallsEquivalent"]),
            "totalApiCallsEquivalent": int(usage["totalApiCallsEquivalent"]),
            "llmCallsByProvider": dict(usage["llmCallsByProvider"]),
            "retrievalCallsByProvider": dict(usage["retrievalCallsByProvider"]),
        }
