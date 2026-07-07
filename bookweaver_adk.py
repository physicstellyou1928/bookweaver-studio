"""Small ADK runner used by the BookWeaver product UI.

The visible web app uses this module for agent reasoning evidence. Full chapter
translation stays in ``bookweaver_runtime`` because the MCP security boundary
intentionally avoids returning complete chapter text to LLM agents.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

APP_NAME = "bookweaver-studio"
USER_ID = "local-translator"


def _has_real_google_key() -> bool:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    return bool(key and "your-" not in key and key != "your-gemini-api-key")


def _part_text(part: Any) -> str:
    return str(getattr(part, "text", "") or "").strip()


def _summarize_event(event: Any) -> dict[str, Any]:
    calls = []
    for call in event.get_function_calls() or []:
        calls.append({"name": getattr(call, "name", ""), "args": getattr(call, "args", {})})

    responses = []
    for response in event.get_function_responses() or []:
        responses.append(
            {
                "name": getattr(response, "name", ""),
                "response": getattr(response, "response", {}),
            }
        )

    text_parts = []
    content = getattr(event, "content", None)
    for part in getattr(content, "parts", []) or []:
        text = _part_text(part)
        if text:
            text_parts.append(text)

    return {
        "author": getattr(event, "author", ""),
        "text": "\n".join(text_parts),
        "function_calls": calls,
        "function_responses": responses,
        "final": bool(event.is_final_response()),
    }


def run_adk_prompt(prompt: str) -> dict[str, Any]:
    """Run the real ADK root_agent once and return a compact trace."""
    if not _has_real_google_key():
        return {
            "ok": False,
            "error": "GOOGLE_API_KEY is not configured; ADK reasoning was skipped.",
            "events": [],
            "final_text": "",
        }

    try:
        from translationtrail.agent import root_agent

        session_service = InMemorySessionService()
        session = session_service.create_session_sync(app_name=APP_NAME, user_id=USER_ID)
        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            session_service=session_service,
        )
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
        events = []
        final_text = ""
        for event in runner.run(
            user_id=USER_ID,
            session_id=session.id,
            new_message=message,
        ):
            summary = _summarize_event(event)
            events.append(summary)
            if summary["final"] and summary["text"]:
                final_text = summary["text"]
        return {"ok": True, "events": events, "final_text": final_text}
    except Exception as exc:  # pragma: no cover - depends on local/network credentials
        return {"ok": False, "error": str(exc), "events": [], "final_text": ""}


def run_adk_planning() -> dict[str, Any]:
    return run_adk_prompt(
        "Use the planning_agent and MCP tools to inspect the workspace. "
        "Report the current progress, the next pending chapter, and a concise "
        "chunking recommendation. Do not request or output full chapter text."
    )


def run_adk_quality(chapter_id: str) -> dict[str, Any]:
    return run_adk_prompt(
        f"Use the quality_agent and MCP tools to check translated output for {chapter_id}. "
        "Report structural status, paragraph availability, and the next verification step. "
        "Do not request or output full chapter text."
    )
