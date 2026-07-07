"""BookWeaver runtime for importing, translating and exporting local books.

This is the user-facing product path for the Kaggle demo. ADK/MCP still exist
as the agent/tool layer, but this module provides the visible "upload book",
"analyze", "translate" and "export" workflow a translator would expect.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from html import escape, unescape
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "sample_workspace"
TEXT_DIR = WORKSPACE / "Text"
TRANSLATED_DIR = WORKSPACE / "Text_translated"
METADATA_DIR = WORKSPACE / "metadata"
EXPORT_DIR = WORKSPACE / "exports"


@dataclass
class ChapterBlock:
    tag: str
    text: str


def ensure_workspace() -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip("-")
    return stem or "chapter"


def _safe_chapter_id(chapter_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", chapter_id or ""):
        raise ValueError(f"Unsafe chapter id: {chapter_id}")
    return chapter_id


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _strip_tags(fragment: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _blocks_from_html(html: str) -> list[ChapterBlock]:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        blocks = []
        for node in soup.find_all(["h1", "h2", "h3", "p"]):
            text = node.get_text(" ", strip=True)
            if text:
                blocks.append(ChapterBlock(tag=node.name, text=text))
        return blocks

    pattern = re.compile(r"<(?P<tag>p|h1|h2|h3)\b[^>]*>(?P<body>.*?)</(?P=tag)>", re.I | re.S)
    return [
        ChapterBlock(tag=m.group("tag").lower(), text=_strip_tags(m.group("body")))
        for m in pattern.finditer(html)
        if _strip_tags(m.group("body"))
    ]


def read_chapter_blocks(chapter_id: str) -> list[ChapterBlock]:
    chapter_id = _safe_chapter_id(chapter_id)
    path = TEXT_DIR / f"{chapter_id}.xhtml"
    if not path.exists():
        raise FileNotFoundError(f"Chapter not found: {chapter_id}")
    return _blocks_from_html(path.read_text(encoding="utf-8"))


def list_chapters() -> list[dict[str, Any]]:
    ensure_workspace()
    chapters = []
    for path in sorted(TEXT_DIR.glob("*.xhtml")):
        translated = TRANSLATED_DIR / path.name
        blocks = read_chapter_blocks(path.stem)
        chars = sum(len(block.text) for block in blocks)
        chapters.append(
            {
                "chapter_id": path.stem,
                "source_file": str(path.relative_to(WORKSPACE)),
                "translated_file": str(translated.relative_to(WORKSPACE)) if translated.exists() else "",
                "status": "translated" if translated.exists() else "pending",
                "blocks": len(blocks),
                "chars": chars,
            }
        )
    return chapters


def project_status() -> dict[str, Any]:
    chapters = list_chapters()
    translated = [chapter for chapter in chapters if chapter["status"] == "translated"]
    pending = [chapter for chapter in chapters if chapter["status"] == "pending"]
    terms = _load_json(METADATA_DIR / "terms.json", {"names": {}, "places": {}, "terms": {}})
    return {
        "chapters_total": len(chapters),
        "chapters_translated": len(translated),
        "next_pending": pending[0]["chapter_id"] if pending else "",
        "term_counts": {
            "names": len(terms.get("names", {})),
            "places": len(terms.get("places", {})),
            "terms": len(terms.get("terms", {})),
        },
    }


def reset_to_sample_book() -> dict[str, Any]:
    """Restore the fabricated sample book shipped with the repo."""
    ensure_workspace()
    # Keep source sample files, but reset generated translation state to the
    # intended demo baseline: ch01 translated, ch02 pending.
    ch01 = TRANSLATED_DIR / "ch01.xhtml"
    ch01.write_text(
        """<html>
  <body>
    <h1>第一章</h1>
    <p class="body">米拉在厨房桌上发现了一个蓝色信封。</p>
    <p class="body">“又是一封官方通知？”她哥哥问。</p>
    <p class="body">她慢慢打开信封，把截止日期写进笔记本。</p>
  </body>
</html>
""",
        encoding="utf-8",
    )
    ch02 = TRANSLATED_DIR / "ch02.xhtml"
    if ch02.exists():
        ch02.unlink()
    _save_json(
        METADATA_DIR / "context.json",
        {
            "current_chapter": "ch01",
            "story_summary": (
                "A translator uses careful notes and glossary memory to handle "
                "long documents over multiple sessions."
            ),
            "chapter_summaries": {
                "ch01": {
                    "summary": "Mira receives a difficult notice and starts tracking the deadline carefully.",
                    "timestamp": "2026-07-07T00:00:00",
                }
            },
        },
    )
    _save_json(
        METADATA_DIR / "terms.json",
        {
            "names": {
                "Mira": {
                    "target": "米拉",
                    "note": "Main character in fabricated demo sample.",
                }
            },
            "places": {},
            "terms": {
                "deadline": {
                    "target": "截止日期",
                    "note": "Keep consistent in action-oriented passages.",
                }
            },
            "updated_at": "2026-07-07T00:00:00",
        },
    )
    return project_status()


def import_epub(epub_path: Path) -> dict[str, Any]:
    """Import text-like chapters from an EPUB zip into the local workspace."""
    ensure_workspace()
    if not zipfile.is_zipfile(epub_path):
        raise ValueError("Please upload a valid .epub file.")

    shutil.rmtree(TEXT_DIR, ignore_errors=True)
    shutil.rmtree(TRANSLATED_DIR, ignore_errors=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        with zipfile.ZipFile(epub_path) as archive:
            for member in archive.infolist():
                name = member.filename
                if name.startswith("/") or ".." in Path(name).parts:
                    continue
                suffix = Path(name).suffix.lower()
                if suffix not in {".xhtml", ".html", ".htm"}:
                    continue
                if any(part.lower() in {"meta-inf"} for part in Path(name).parts):
                    continue
                archive.extract(member, temp)

        candidates = []
        for path in temp.rglob("*"):
            if path.suffix.lower() not in {".xhtml", ".html", ".htm"}:
                continue
            stem = path.stem.lower()
            if stem in {"cover", "toc", "nav", "title", "copyright"}:
                continue
            blocks = _blocks_from_html(path.read_text(encoding="utf-8", errors="ignore"))
            if not blocks:
                continue
            candidates.append((path, blocks))

        if not candidates:
            raise ValueError("No readable XHTML/HTML chapters found in this EPUB.")

        for idx, (path, _blocks) in enumerate(sorted(candidates), start=1):
            chapter_id = f"ch{idx:02d}-{_safe_stem(path.name)}"
            shutil.copyfile(path, TEXT_DIR / f"{chapter_id}.xhtml")

    _save_json(
        METADATA_DIR / "context.json",
        {
            "current_chapter": None,
            "story_summary": f"Imported from {epub_path.name}.",
            "chapter_summaries": {},
            "updated_at": datetime.now().isoformat(),
        },
    )
    _save_json(
        METADATA_DIR / "terms.json",
        {"names": {}, "places": {}, "terms": {}, "updated_at": datetime.now().isoformat()},
    )
    return project_status()


def analyze_book() -> dict[str, Any]:
    chapters = list_chapters()
    total_chars = sum(chapter["chars"] for chapter in chapters)
    pending = [chapter["chapter_id"] for chapter in chapters if chapter["status"] == "pending"]
    return {
        "status": project_status(),
        "total_chars": total_chars,
        "pending_chapters": pending,
        "recommendation": (
            f"Translate {pending[0]} next." if pending else "All chapters are translated."
        ),
    }


def _has_real_google_key() -> bool:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    return bool(key and "your-" not in key and key != "your-gemini-api-key")


def _demo_translate(text: str, target_language: str) -> str:
    """Fallback translator for recording UI flow without a key."""
    return f"[demo {target_language}] {text}"


def _gemini_translate(text: str, target_language: str) -> str:
    from google import genai

    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = os.environ.get("TRANSLATIONTRAIL_MODEL", "gemini-3.5-flash")
    prompt = (
        "Translate the following literary passage into "
        f"{target_language}. Preserve meaning, names and tone. Return only the translation.\n\n"
        f"{text}"
    )
    response = client.models.generate_content(model=model, contents=prompt)
    return (response.text or "").strip()


def translate_next_chapter(target_language: str = "Chinese", demo_mode: bool = False) -> dict[str, Any]:
    chapters = list_chapters()
    pending = [chapter for chapter in chapters if chapter["status"] == "pending"]
    if not pending:
        return {"ok": False, "message": "All chapters are already translated."}

    chapter_id = pending[0]["chapter_id"]
    blocks = read_chapter_blocks(chapter_id)
    use_demo = demo_mode or not _has_real_google_key()
    translated_blocks = []
    for block in blocks:
        translated = (
            _demo_translate(block.text, target_language)
            if use_demo
            else _gemini_translate(block.text, target_language)
        )
        translated_blocks.append(ChapterBlock(tag=block.tag, text=translated))

    output = ["<html>", "  <body>"]
    for block in translated_blocks:
        tag = "h1" if block.tag in {"h1", "h2", "h3"} else "p"
        output.append(f'    <{tag} class="translated">{escape(block.text)}</{tag}>')
    output.extend(["  </body>", "</html>", ""])
    output_path = TRANSLATED_DIR / f"{chapter_id}.xhtml"
    output_path.write_text("\n".join(output), encoding="utf-8")

    context = _load_json(METADATA_DIR / "context.json", {"chapter_summaries": {}})
    context["current_chapter"] = chapter_id
    context.setdefault("chapter_summaries", {})[chapter_id] = {
        "summary": f"{chapter_id} translated into {target_language}.",
        "timestamp": datetime.now().isoformat(),
    }
    context["updated_at"] = datetime.now().isoformat()
    _save_json(METADATA_DIR / "context.json", context)

    return {
        "ok": True,
        "chapter_id": chapter_id,
        "output_file": str(output_path.relative_to(WORKSPACE)),
        "mode": "demo" if use_demo else "gemini",
        "blocks_translated": len(blocks),
    }


def preview_translation(chapter_id: str, max_blocks: int = 12, max_chars: int = 1200) -> dict[str, Any]:
    """Return a bounded side-by-side preview for one translated chapter."""
    ensure_workspace()
    chapter_id = _safe_chapter_id(chapter_id)
    source_path = TEXT_DIR / f"{chapter_id}.xhtml"
    translated_path = TRANSLATED_DIR / f"{chapter_id}.xhtml"
    if not source_path.exists():
        return {"ok": False, "message": f"Source chapter not found: {chapter_id}"}
    if not translated_path.exists():
        return {"ok": False, "message": f"No translated output for: {chapter_id}"}

    def payload(block: ChapterBlock) -> dict[str, str]:
        text = block.text
        if len(text) > max_chars:
            text = f"{text[:max_chars].rstrip()}..."
        return {"tag": block.tag, "text": text}

    all_source_blocks = _blocks_from_html(source_path.read_text(encoding="utf-8"))
    all_translated_blocks = _blocks_from_html(translated_path.read_text(encoding="utf-8"))
    source_blocks = all_source_blocks[:max_blocks]
    translated_blocks = all_translated_blocks[:max_blocks]
    return {
        "ok": True,
        "chapter_id": chapter_id,
        "source_file": str(source_path.relative_to(WORKSPACE)),
        "translated_file": str(translated_path.relative_to(WORKSPACE)),
        "source_blocks": [payload(block) for block in source_blocks],
        "translated_blocks": [payload(block) for block in translated_blocks],
        "truncated": len(all_source_blocks) > max_blocks or len(all_translated_blocks) > max_blocks,
    }


def export_translated_package() -> Path:
    ensure_workspace()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = EXPORT_DIR / f"bookweaver-translated-{timestamp}.zip"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for base in [TRANSLATED_DIR, METADATA_DIR]:
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(WORKSPACE))
    return out_path
