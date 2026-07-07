"""Product-level agent workflow for BookWeaver Studio.

The ADK app in ``translationtrail/`` demonstrates Google ADK multi-agent
orchestration. This module wires the visible product UI to the same conceptual
agent split so the demo is not just a UI shell over plain helper functions.

Each product agent has a narrow responsibility and must use the MCP store
functions for project state, analysis, memory and quality checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp_server import store

import bookweaver_runtime as runtime


@dataclass
class AgentTrace:
    """Small trace object shown in the product UI."""

    steps: list[dict[str, Any]] = field(default_factory=list)

    def add(self, agent: str, action: str, tool: str, result: Any) -> Any:
        self.steps.append(
            {
                "agent": agent,
                "action": action,
                "tool": tool,
                "result": result,
            }
        )
        return result


class PlanningAgent:
    name = "planning_agent"

    def analyze_book(self, trace: AgentTrace) -> dict[str, Any]:
        status = trace.add(
            self.name,
            "Read workspace status",
            "mcp.get_project_status",
            store.get_project_status(ws=runtime.WORKSPACE),
        )
        chapters = trace.add(
            self.name,
            "List chapter states",
            "mcp.list_chapters",
            store.list_chapters({"limit": 100}, ws=runtime.WORKSPACE),
        )
        pending = [
            chapter["chapter_id"]
            for chapter in chapters["chapters"]
            if chapter["status"] == "pending"
        ]
        next_chapter = pending[0] if pending else None
        next_analysis = None
        if next_chapter:
            next_analysis = trace.add(
                self.name,
                "Analyze next pending chapter",
                "mcp.analyze_chapter",
                store.analyze_chapter({"chapter_id": next_chapter}, ws=runtime.WORKSPACE),
            )
        return {
            "status": status,
            "chapters": chapters["chapters"],
            "next_chapter": next_chapter,
            "next_analysis": next_analysis,
            "recommendation": (
                f"Translate {next_chapter} next using {next_analysis['suggested_strategy']}."
                if next_chapter and next_analysis
                else "All chapters are translated."
            ),
        }


class TranslationAgent:
    name = "translation_agent"

    def translate_next(
        self,
        target_language: str,
        demo_mode: bool,
        trace: AgentTrace,
    ) -> dict[str, Any]:
        plan = PlanningAgent().analyze_book(trace)
        chapter_id = plan.get("next_chapter")
        if not chapter_id:
            return {"ok": False, "message": "All chapters are already translated."}
        trace.add(
            self.name,
            "Translate planned chapter",
            "runtime.translate_next_chapter",
            {"chapter_id": chapter_id, "target_language": target_language, "demo_mode": demo_mode},
        )
        return runtime.translate_next_chapter(
            target_language=target_language,
            demo_mode=demo_mode,
        )


class MemoryAgent:
    name = "memory_agent"

    def record_translation(self, chapter_id: str, target_language: str, trace: AgentTrace) -> dict[str, Any]:
        summary = trace.add(
            self.name,
            "Record bounded chapter summary",
            "mcp.record_chapter_summary",
            store.record_chapter_summary(
                {
                    "chapter_id": chapter_id,
                    "summary": f"{chapter_id} was translated into {target_language}.",
                },
                ws=runtime.WORKSPACE,
            ),
        )
        decision = trace.add(
            self.name,
            "Record translation decision",
            "mcp.record_translation_decision",
            store.record_translation_decision(
                {
                    "chapter_id": chapter_id,
                    "decision_type": "translation_completed",
                    "rationale": (
                        "The product workflow translated the next pending chapter "
                        "after the planning agent selected it."
                    ),
                },
                ws=runtime.WORKSPACE,
            ),
        )
        return {"summary": summary, "decision": decision}


class QualityAgent:
    name = "quality_agent"

    def check(self, chapter_id: str, trace: AgentTrace) -> dict[str, Any]:
        return trace.add(
            self.name,
            "Check translated chapter structure",
            "mcp.get_quality_status",
            store.get_quality_status({"chapter_id": chapter_id}, ws=runtime.WORKSPACE),
        )


def run_analysis_workflow() -> dict[str, Any]:
    """Run the visible product analysis through the planning agent."""
    trace = AgentTrace()
    analysis = PlanningAgent().analyze_book(trace)
    return {"analysis": analysis, "agent_trace": trace.steps}


def run_translation_workflow(target_language: str, demo_mode: bool) -> dict[str, Any]:
    """Run product translation through planner, translator, memory and quality agents."""
    trace = AgentTrace()
    translated = TranslationAgent().translate_next(target_language, demo_mode, trace)
    memory = None
    quality = None
    if translated.get("ok"):
        chapter_id = translated["chapter_id"]
        memory = MemoryAgent().record_translation(chapter_id, target_language, trace)
        quality = QualityAgent().check(chapter_id, trace)
    return {
        "translation": translated,
        "memory": memory,
        "quality": quality,
        "agent_trace": trace.steps,
    }

