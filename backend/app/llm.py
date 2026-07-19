from __future__ import annotations

import json
import os
from typing import Any

from .prompts import build_sql_messages, build_summary_messages

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency at runtime
    OpenAI = None  # type: ignore[assignment]


_SQL_PLAN_CACHE: dict[tuple[str, str | None], dict[str, Any] | None] = {}


def _extract_json(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text[:-3]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def llm_settings() -> dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    available = bool(api_key) and OpenAI is not None
    return {
        "available": available,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
        "missing_dependency": OpenAI is None,
    }


def llm_mode_payload() -> dict[str, Any]:
    settings = llm_settings()
    if settings["available"]:
        return {
            "mode": "online",
            "label": "DeepSeek 在线增强模式",
            "llm_available": True,
            "model": settings["model"],
        }
    return {
        "mode": "offline",
        "label": "离线演示模式",
        "llm_available": False,
        "model": settings["model"] if not settings["missing_dependency"] else None,
    }


def _client() -> Any | None:
    settings = llm_settings()
    if not settings["available"]:
        return None
    return OpenAI(api_key=settings["api_key"], base_url=settings["base_url"])


def generate_sql_plan(question: str, class_context: str | None = None) -> dict[str, Any] | None:
    cache_key = (question.strip(), class_context)
    if cache_key in _SQL_PLAN_CACHE:
        return _SQL_PLAN_CACHE[cache_key]

    client = _client()
    if client is None:
        _SQL_PLAN_CACHE[cache_key] = None
        return None

    settings = llm_settings()
    try:
        response = client.chat.completions.create(
            model=settings["model"],
            messages=build_sql_messages(question, class_context),
            temperature=0.1,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed = _extract_json(content)
        _SQL_PLAN_CACHE[cache_key] = parsed
        return parsed
    except Exception:
        _SQL_PLAN_CACHE[cache_key] = None
        return None


def summarize_result(payload: dict[str, Any]) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    settings = llm_settings()
    try:
        response = client.chat.completions.create(
            model=settings["model"],
            messages=build_summary_messages(payload),
            temperature=0.2,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return _extract_json(content)
    except Exception:
        return None
