"""Deterministic workspace operations behind the TranslationTrail MCP server."""

from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any

MAX_TEXT_LEN = 2_000
MAX_ITEMS = 100
TERM_CATEGORIES = {"names", "places", "terms"}


class ValidationError(ValueError):
    """Raised when MCP tool arguments fail validation."""


def workspace_root(root: str | Path | None = None, workspace: str | Path | None = None) -> Path:
    base = Path(root).resolve() if root else Path(__file__).resolve().parent.parent
    return (base / (workspace or "sample_workspace")).resolve()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _text(value: Any, field: str, *, max_len: int = MAX_TEXT_LEN, required: bool = True) -> str:
    if value in (None, "") and not required:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > max_len:
        raise ValidationError(f"{field} exceeds {max_len} characters")
    return value


def _chapter_id(value: Any) -> str:
    chapter = _text(value, "chapter_id", max_len=120).removesuffix(".xhtml")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", chapter):
        raise ValidationError("chapter_id must be a safe file stem")
    return chapter


def _strip_tags(fragment: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _blocks(path: Path) -> list[tuple[str, str]]:
    html = path.read_text(encoding="utf-8")
    pattern = re.compile(r"<(?P<tag>p|h1|h2|h3)\b[^>]*>(?P<body>.*?)</(?P=tag)>", re.I | re.S)
    return [(m.group("tag").lower(), _strip_tags(m.group("body"))) for m in pattern.finditer(html)]


def _stats(path: Path) -> dict[str, Any]:
    paragraphs = [text for tag, text in _blocks(path) if tag == "p" and text]
    all_text = [text for _tag, text in _blocks(path) if text]
    chars = sum(len(text) for text in all_text)
    dialog_count = sum(1 for text in paragraphs if any(mark in text for mark in "\"'“”‘’"))
    return {
        "chars": chars,
        "words": sum(len(text.split()) for text in all_text),
        "paragraph_count": len(paragraphs),
        "dialog_count": dialog_count,
    }


def _chapters(ws: Path) -> list[Path]:
    return sorted((ws / "Text").glob("*.xhtml"))


def _translated_path(ws: Path, chapter_id: str) -> Path | None:
    path = ws / "Text_translated" / f"{chapter_id}.xhtml"
    return path if path.exists() else None


def _suggest_strategy(stats: dict[str, Any]) -> str:
    chars = stats["chars"]
    paragraphs = stats["paragraph_count"] or 1
    dialog_ratio = stats["dialog_count"] / paragraphs
    if chars < 1_500:
        return "short_chapter"
    if dialog_ratio >= 0.55:
        return "dialog_heavy"
    if dialog_ratio <= 0.20:
        return "narrative_heavy"
    return "default"


def log_audit(ws: Path, tool_name: str, arguments: dict[str, Any], status: str) -> None:
    path = ws / "metadata" / "mcp_audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "status": status,
        "arguments": arguments,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_project_status(arguments: dict[str, Any] | None = None, *, ws: Path) -> dict[str, Any]:
    chapters = _chapters(ws)
    translated = sum(1 for chapter in chapters if _translated_path(ws, chapter.stem))
    context = _load_json(ws / "metadata" / "context.json", {})
    terms = _load_json(ws / "metadata" / "terms.json", {"names": {}, "places": {}, "terms": {}})
    return {
        "chapters_total": len(chapters),
        "chapters_translated": translated,
        "next_pending": next((c.stem for c in chapters if not _translated_path(ws, c.stem)), None),
        "current_chapter": context.get("current_chapter"),
        "term_counts": {category: len(terms.get(category, {})) for category in sorted(TERM_CATEGORIES)},
        "note": "MCP returns metadata and statistics, not full chapter text.",
    }


def list_chapters(arguments: dict[str, Any] | None = None, *, ws: Path) -> dict[str, Any]:
    limit = int((arguments or {}).get("limit", MAX_ITEMS))
    if limit < 1 or limit > MAX_ITEMS:
        raise ValidationError(f"limit must be between 1 and {MAX_ITEMS}")
    items = []
    for chapter in _chapters(ws)[:limit]:
        translated = _translated_path(ws, chapter.stem)
        items.append(
            {
                "chapter_id": chapter.stem,
                "source_file": str(chapter.relative_to(ws)),
                "translated_file": str(translated.relative_to(ws)) if translated else None,
                "status": "translated" if translated else "pending",
            }
        )
    return {"chapters": items}


def analyze_chapter(arguments: dict[str, Any], *, ws: Path) -> dict[str, Any]:
    chapter_id = _chapter_id(arguments.get("chapter_id"))
    path = ws / "Text" / f"{chapter_id}.xhtml"
    if not path.exists():
        raise ValidationError(f"chapter not found: {chapter_id}")
    stats = _stats(path)
    return {
        "chapter_id": chapter_id,
        "source_file": str(path.relative_to(ws)),
        "basic_stats": stats,
        "suggested_strategy": _suggest_strategy(stats),
        "estimated_chunks": max(1, (stats["chars"] + 1_499) // 1_500),
        "notes": ["No full prose returned; use deterministic translator pipeline for text extraction."],
    }


def get_context_snapshot(arguments: dict[str, Any] | None = None, *, ws: Path) -> dict[str, Any]:
    context = _load_json(ws / "metadata" / "context.json", {})
    summaries = context.get("chapter_summaries", {})
    recent_keys = sorted(summaries.keys())[-5:] if isinstance(summaries, dict) else []
    return {
        "current_chapter": context.get("current_chapter"),
        "story_summary": str(context.get("story_summary", ""))[:MAX_TEXT_LEN],
        "recent_chapter_summaries": {key: summaries[key] for key in recent_keys},
    }


def list_terms(arguments: dict[str, Any] | None = None, *, ws: Path) -> dict[str, Any]:
    args = arguments or {}
    category = args.get("category")
    limit = int(args.get("limit", 50))
    if limit < 1 or limit > MAX_ITEMS:
        raise ValidationError(f"limit must be between 1 and {MAX_ITEMS}")
    terms = _load_json(ws / "metadata" / "terms.json", {"names": {}, "places": {}, "terms": {}})
    categories = [category] if category else sorted(TERM_CATEGORIES)
    result = {}
    for item in categories:
        if item not in TERM_CATEGORIES:
            raise ValidationError(f"unknown term category: {item}")
        result[item] = dict(list(terms.get(item, {}).items())[:limit])
    return result


def upsert_term(arguments: dict[str, Any], *, ws: Path) -> dict[str, Any]:
    category = _text(arguments.get("category"), "category", max_len=20)
    if category not in TERM_CATEGORIES:
        raise ValidationError(f"category must be one of {sorted(TERM_CATEGORIES)}")
    source = _text(arguments.get("source"), "source", max_len=160)
    target = _text(arguments.get("target"), "target", max_len=160, required=False)
    note = _text(arguments.get("note"), "note", required=False)
    path = ws / "metadata" / "terms.json"
    terms = _load_json(path, {"names": {}, "places": {}, "terms": {}})
    entry = terms.setdefault(category, {}).get(source, {})
    if target:
        entry["target"] = target
    if note:
        entry["note"] = note
    entry["updated_at"] = datetime.now().isoformat()
    terms[category][source] = entry
    terms["updated_at"] = datetime.now().isoformat()
    _save_json(path, terms)
    return {"ok": True, "category": category, "source": source, "entry": entry}


def record_chapter_summary(arguments: dict[str, Any], *, ws: Path) -> dict[str, Any]:
    chapter_id = _chapter_id(arguments.get("chapter_id"))
    summary = _text(arguments.get("summary"), "summary")
    path = ws / "metadata" / "context.json"
    context = _load_json(path, {})
    context.setdefault("chapter_summaries", {})[chapter_id] = {
        "summary": summary,
        "timestamp": datetime.now().isoformat(),
    }
    context["current_chapter"] = chapter_id
    context["updated_at"] = datetime.now().isoformat()
    _save_json(path, context)
    return {"ok": True, "chapter_id": chapter_id}


def record_translation_decision(arguments: dict[str, Any], *, ws: Path) -> dict[str, Any]:
    chapter_id = _chapter_id(arguments.get("chapter_id"))
    decision_type = _text(arguments.get("decision_type"), "decision_type", max_len=80)
    rationale = _text(arguments.get("rationale"), "rationale")
    path = ws / "metadata" / "agent_decisions.json"
    decisions = _load_json(path, [])
    if not isinstance(decisions, list):
        decisions = []
    entry = {
        "timestamp": datetime.now().isoformat(),
        "chapter_id": chapter_id,
        "decision_type": decision_type,
        "rationale": rationale,
    }
    decisions.append(entry)
    _save_json(path, decisions[-500:])
    return {"ok": True, "recorded": entry}


def get_quality_status(arguments: dict[str, Any], *, ws: Path) -> dict[str, Any]:
    chapter_id = _chapter_id(arguments.get("chapter_id"))
    source = ws / "Text" / f"{chapter_id}.xhtml"
    if not source.exists():
        raise ValidationError(f"chapter not found: {chapter_id}")
    translated = _translated_path(ws, chapter_id)
    source_stats = _stats(source)
    result = {
        "chapter_id": chapter_id,
        "status": "translated" if translated else "pending",
        "source": source_stats,
    }
    if translated:
        translated_stats = _stats(translated)
        result["translated"] = translated_stats
        result["paragraph_delta"] = translated_stats["paragraph_count"] - source_stats["paragraph_count"]
        result["char_ratio"] = round(translated_stats["chars"] / source_stats["chars"], 3) if source_stats["chars"] else None
    return result

