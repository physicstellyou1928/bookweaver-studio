from __future__ import annotations

from pathlib import Path

import pytest

import bookweaver_runtime as runtime


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_preview_translation_returns_bounded_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "sample_workspace"
    monkeypatch.setattr(runtime, "WORKSPACE", workspace)
    monkeypatch.setattr(runtime, "TEXT_DIR", workspace / "Text")
    monkeypatch.setattr(runtime, "TRANSLATED_DIR", workspace / "Text_translated")
    monkeypatch.setattr(runtime, "METADATA_DIR", workspace / "metadata")
    monkeypatch.setattr(runtime, "EXPORT_DIR", workspace / "exports")

    write(runtime.TEXT_DIR / "ch01.xhtml", "<html><body><p>Source sentence.</p></body></html>")
    write(
        runtime.TRANSLATED_DIR / "ch01.xhtml",
        "<html><body><p>Translated sentence.</p></body></html>",
    )

    preview = runtime.preview_translation("ch01")

    assert preview["ok"] is True
    assert preview["chapter_id"] == "ch01"
    assert preview["source_blocks"][0]["text"] == "Source sentence."
    assert preview["translated_blocks"][0]["text"] == "Translated sentence."


def test_preview_translation_rejects_unsafe_chapter_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "sample_workspace"
    monkeypatch.setattr(runtime, "WORKSPACE", workspace)

    with pytest.raises(ValueError):
        runtime.preview_translation("../secret")
