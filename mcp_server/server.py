"""TranslationTrail MCP server over stdio."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Callable

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_server import store

ROOT = Path(os.environ.get("TRANSLATIONTRAIL_ROOT", Path(__file__).resolve().parent.parent)).resolve()
WORKSPACE = os.environ.get("TRANSLATIONTRAIL_WORKSPACE", "sample_workspace")
WS = store.workspace_root(ROOT, WORKSPACE)

server = Server("translationtrail-workspace")
Handler = Callable[[dict], dict]


def _handler(fn):
    return lambda arguments: fn(arguments, ws=WS)


_HANDLERS: dict[str, tuple[Handler, str]] = {
    "get_project_status": (_handler(store.get_project_status), "read"),
    "list_chapters": (_handler(store.list_chapters), "read"),
    "analyze_chapter": (_handler(store.analyze_chapter), "read"),
    "get_context_snapshot": (_handler(store.get_context_snapshot), "read"),
    "list_terms": (_handler(store.list_terms), "read"),
    "get_quality_status": (_handler(store.get_quality_status), "read"),
    "upsert_term": (_handler(store.upsert_term), "write"),
    "record_chapter_summary": (_handler(store.record_chapter_summary), "write"),
    "record_translation_decision": (_handler(store.record_translation_decision), "write"),
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    text = {"type": "string", "maxLength": store.MAX_TEXT_LEN}
    chapter_id = {"type": "string", "description": "Safe chapter stem, e.g. ch01"}
    return [
        Tool(
            name="get_project_status",
            description="[read] Translation progress, next pending chapter and term counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_chapters",
            description="[read] List source chapters and translation availability.",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": store.MAX_ITEMS}},
            },
        ),
        Tool(
            name="analyze_chapter",
            description="[read] Analyze chapter shape and suggest a chunking strategy.",
            inputSchema={"type": "object", "properties": {"chapter_id": chapter_id}, "required": ["chapter_id"]},
        ),
        Tool(
            name="get_context_snapshot",
            description="[read] Bounded translation memory snapshot.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_terms",
            description="[read] Bounded glossary entries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": sorted(store.TERM_CATEGORIES)},
                    "limit": {"type": "integer", "minimum": 1, "maximum": store.MAX_ITEMS},
                },
            },
        ),
        Tool(
            name="get_quality_status",
            description="[read] Structural quality status for one chapter.",
            inputSchema={"type": "object", "properties": {"chapter_id": chapter_id}, "required": ["chapter_id"]},
        ),
        Tool(
            name="upsert_term",
            description="[write] Add or update one glossary item.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": sorted(store.TERM_CATEGORIES)},
                    "source": {"type": "string", "maxLength": 160},
                    "target": {"type": "string", "maxLength": 160},
                    "note": text,
                },
                "required": ["category", "source"],
            },
        ),
        Tool(
            name="record_chapter_summary",
            description="[write] Save a bounded chapter summary.",
            inputSchema={"type": "object", "properties": {"chapter_id": chapter_id, "summary": text}, "required": ["chapter_id", "summary"]},
        ),
        Tool(
            name="record_translation_decision",
            description="[write] Record an agent decision for traceability.",
            inputSchema={
                "type": "object",
                "properties": {"chapter_id": chapter_id, "decision_type": {"type": "string"}, "rationale": text},
                "required": ["chapter_id", "decision_type", "rationale"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    entry = _HANDLERS.get(name)
    if entry is None:
        store.log_audit(WS, name, arguments or {}, "rejected: unknown tool")
        return [TextContent(type="text", text=f"Error: unknown tool '{name}'")]
    handler, _access = entry
    try:
        result = handler(arguments or {})
    except store.ValidationError as exc:
        store.log_audit(WS, name, arguments or {}, f"rejected: {exc}")
        return [TextContent(type="text", text=f"Error: {exc}")]
    store.log_audit(WS, name, arguments or {}, "ok")
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

