"""TranslationTrail ADK agent tree."""

from __future__ import annotations

import os
import sys

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from mcp.client.stdio import get_default_environment

from translationtrail import prompts
from translationtrail.config import MODEL, REPO_ROOT, WORKSPACE
from translationtrail.guardrails import screen_for_injection, validate_tool_args


def _mcp_slice(tool_names: list[str], *, confirm: bool = False) -> McpToolset:
    """Create a filtered MCP tool view for one specialist."""
    env = get_default_environment()
    env["TRANSLATIONTRAIL_ROOT"] = str(REPO_ROOT)
    env["TRANSLATIONTRAIL_WORKSPACE"] = str(WORKSPACE)
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_server.server"],
                cwd=str(REPO_ROOT),
                env=env,
            ),
            timeout=30,
        ),
        tool_filter=tool_names,
        require_confirmation=confirm,
    )


_CONFIRM_WRITES = os.environ.get("TRANSLATIONTRAIL_CONFIRM_WRITES", "").upper() == "TRUE"

planning_agent = LlmAgent(
    name="planning_agent",
    model=MODEL,
    description="Plans next translation steps from progress and chapter analysis.",
    instruction=prompts.PLANNING_INSTRUCTION,
    tools=[
        _mcp_slice(
            [
                "get_project_status",
                "list_chapters",
                "analyze_chapter",
                "get_context_snapshot",
            ]
        )
    ],
    before_model_callback=screen_for_injection,
    before_tool_callback=validate_tool_args,
)

terminology_agent = LlmAgent(
    name="terminology_agent",
    model=MODEL,
    description="Maintains names, places and terminology.",
    instruction=prompts.TERMINOLOGY_INSTRUCTION,
    tools=[_mcp_slice(["list_terms", "upsert_term"], confirm=_CONFIRM_WRITES)],
    before_model_callback=screen_for_injection,
    before_tool_callback=validate_tool_args,
)

memory_agent = LlmAgent(
    name="memory_agent",
    model=MODEL,
    description="Records bounded chapter summaries and translation decisions.",
    instruction=prompts.MEMORY_INSTRUCTION,
    tools=[
        _mcp_slice(
            ["get_context_snapshot", "record_chapter_summary", "record_translation_decision"],
            confirm=_CONFIRM_WRITES,
        )
    ],
    before_model_callback=screen_for_injection,
    before_tool_callback=validate_tool_args,
)

quality_agent = LlmAgent(
    name="quality_agent",
    model=MODEL,
    description="Checks translated chapter availability and structural quality.",
    instruction=prompts.QUALITY_INSTRUCTION,
    tools=[_mcp_slice(["get_quality_status", "list_chapters", "get_project_status"])],
    before_model_callback=screen_for_injection,
    before_tool_callback=validate_tool_args,
)

root_agent = LlmAgent(
    name="translation_trail",
    model=MODEL,
    description="Coordinator for TranslationTrail.",
    instruction=prompts.ROOT_INSTRUCTION,
    sub_agents=[planning_agent, terminology_agent, memory_agent, quality_agent],
    before_model_callback=screen_for_injection,
)

