from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server import store


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_status_and_analysis_do_not_return_full_text(tmp_path: Path):
    ws = store.workspace_root(tmp_path)
    write(ws / "Text" / "ch01.xhtml", "<html><body><p>Secret sample sentence.</p></body></html>")
    write(ws / "Text_translated" / "ch01.xhtml", "<html><body><p>示例译文。</p></body></html>")

    status = store.get_project_status(ws=ws)
    analysis = store.analyze_chapter({"chapter_id": "ch01"}, ws=ws)
    payload = json.dumps({"status": status, "analysis": analysis}, ensure_ascii=False)

    assert status["chapters_total"] == 1
    assert status["chapters_translated"] == 1
    assert analysis["basic_stats"]["paragraph_count"] == 1
    assert "Secret sample sentence" not in payload


def test_term_and_summary_writes(tmp_path: Path):
    ws = store.workspace_root(tmp_path)
    term = store.upsert_term(
        {"category": "names", "source": "Mira", "target": "米拉", "note": "demo name"},
        ws=ws,
    )
    summary = store.record_chapter_summary(
        {"chapter_id": "ch01", "summary": "A short original summary."},
        ws=ws,
    )

    assert term["ok"] is True
    assert summary["ok"] is True
    terms = json.loads((ws / "metadata" / "terms.json").read_text(encoding="utf-8"))
    context = json.loads((ws / "metadata" / "context.json").read_text(encoding="utf-8"))
    assert terms["names"]["Mira"]["target"] == "米拉"
    assert context["chapter_summaries"]["ch01"]["summary"] == "A short original summary."


def test_rejects_unsafe_chapter_id(tmp_path: Path):
    ws = store.workspace_root(tmp_path)
    with pytest.raises(store.ValidationError):
        store.analyze_chapter({"chapter_id": "../ch01"}, ws=ws)

