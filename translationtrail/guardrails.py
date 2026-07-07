"""Small ADK guardrails for TranslationTrail."""

from __future__ import annotations

import re
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all )?(previous|prior) instructions", re.I),
    re.compile(r"disregard (all )?(previous|prior) instructions", re.I),
    re.compile(r"reveal (the )?(system|developer) prompt", re.I),
    re.compile(r"delete .*metadata", re.I),
]

_WRITE_TOOLS = {"upsert_term", "record_chapter_summary", "record_translation_decision"}
_WRITE_AGENTS = {"terminology_agent", "memory_agent"}


def _request_text(request: LlmRequest) -> str:
    chunks: list[str] = []
    for content in request.contents or []:
        for part in content.parts or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def screen_for_injection(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Block obvious prompt-injection attempts before the model call."""
    text = _request_text(llm_request)
    if any(pattern.search(text) for pattern in _INJECTION_PATTERNS):
        callback_context.state["blocked_prompt_injection"] = True
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="I blocked that request because it tries to override workspace rules.")],
            )
        )
    return None


def validate_tool_args(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """Enforce least privilege and bounded arguments before MCP calls."""
    if tool.name in _WRITE_TOOLS and tool_context.agent_name not in _WRITE_AGENTS:
        return {"error": f"{tool.name} is not permitted for {tool_context.agent_name}"}

    chapter_id = args.get("chapter_id")
    if chapter_id is not None:
        safe = chapter_id.removesuffix(".xhtml") if isinstance(chapter_id, str) else ""
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", safe):
            return {"error": "chapter_id must be a safe file stem"}

    category = args.get("category")
    if category is not None and category not in {"names", "places", "terms"}:
        return {"error": "category must be names, places, or terms"}

    for key in ("summary", "rationale", "note"):
        value = args.get(key)
        if isinstance(value, str) and len(value) > 2_000:
            return {"error": f"{key} is too long"}

    tool_context.state.setdefault("tool_audit", []).append(
        {"agent": tool_context.agent_name, "tool": tool.name, "args": args}
    )
    return None

