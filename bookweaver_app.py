"""BookWeaver Studio: local recording UI for the capstone demo."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

import bookweaver_runtime as runtime
from bookweaver_agents import run_analysis_workflow, run_translation_workflow

load_dotenv()
runtime.ensure_workspace()

app = FastAPI(title="BookWeaver Studio")


def _status_block() -> str:
    status = runtime.project_status()
    chapters = runtime.list_chapters()
    rows = "\n".join(
        f"""
        <tr>
          <td>{chapter['chapter_id']}</td>
          <td>{chapter['status']}</td>
          <td>{chapter['blocks']}</td>
          <td>{chapter['chars']}</td>
        </tr>
        """
        for chapter in chapters
    )
    return f"""
    <section class="panel">
      <h2>Workspace</h2>
      <div class="metrics">
        <div><strong>{status['chapters_total']}</strong><span>chapters</span></div>
        <div><strong>{status['chapters_translated']}</strong><span>translated</span></div>
        <div><strong>{status['next_pending'] or 'done'}</strong><span>next</span></div>
      </div>
      <table>
        <thead><tr><th>Chapter</th><th>Status</th><th>Blocks</th><th>Chars</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _render(message: str = "", detail: object | None = None) -> HTMLResponse:
    detail_html = ""
    if detail is not None:
        detail_html = f"<pre>{json.dumps(detail, ensure_ascii=False, indent=2)}</pre>"

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BookWeaver Studio</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #5d6872;
      --line: #d8e0e6;
      --bg: #f7f9fb;
      --panel: #ffffff;
      --accent: #1c7f6e;
      --accent-dark: #126154;
      --warm: #f2a65a;
    }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      padding: 28px 40px 18px;
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 16px; font-size: 20px; letter-spacing: 0; }}
    p {{ color: var(--muted); max-width: 860px; line-height: 1.5; }}
    main {{
      display: grid;
      grid-template-columns: minmax(320px, 420px) 1fr;
      gap: 20px;
      padding: 22px 40px 40px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 18px;
    }}
    .stack {{ display: grid; gap: 12px; }}
    label {{ display: block; font-weight: 650; margin-bottom: 6px; }}
    input[type="file"], input[type="text"] {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      font-size: 14px;
      background: #fff;
    }}
    button, .button {{
      width: 100%;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      padding: 11px 12px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      text-align: center;
      text-decoration: none;
      display: inline-block;
      box-sizing: border-box;
    }}
    button.secondary {{ background: #25313a; }}
    button.warm {{ background: var(--warm); color: #1d160f; }}
    button:hover, .button:hover {{ filter: brightness(0.96); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 18px;
    }}
    .metrics div {{
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .metrics strong {{ display: block; font-size: 22px; }}
    .metrics span {{ color: var(--muted); font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    pre {{
      white-space: pre-wrap;
      background: #102027;
      color: #d8fff5;
      padding: 16px;
      border-radius: 8px;
      overflow: auto;
      max-height: 420px;
    }}
    .message {{
      border-left: 4px solid var(--accent);
      background: #eaf7f4;
      padding: 12px 14px;
      border-radius: 6px;
      margin-bottom: 18px;
      color: #174a41;
    }}
    @media (max-width: 900px) {{
      main {{ grid-template-columns: 1fr; padding: 18px; }}
      header {{ padding: 22px 18px 14px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>BookWeaver Studio</h1>
    <p>A local AI translation workspace: upload an EPUB, analyze chapter structure, execute translation, and export a translated package.</p>
  </header>
  <main>
    <aside>
      <section class="panel stack">
        <h2>1. Submit A Book</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
          <label>Upload EPUB</label>
          <input type="file" name="file" accept=".epub" />
          <button type="submit">Upload Book</button>
        </form>
        <form action="/sample" method="post">
          <button class="secondary" type="submit">Use Sample Book</button>
        </form>
      </section>

      <section class="panel stack">
        <h2>2. Agent Analysis</h2>
        <form action="/analyze" method="post">
          <button type="submit">Run Planner Agent</button>
        </form>
      </section>

      <section class="panel stack">
        <h2>3. Execute Translation</h2>
        <form action="/translate-next" method="post">
          <label>Target language</label>
          <input type="text" name="target_language" value="Chinese" />
          <label><input type="checkbox" name="demo_mode" value="true" /> demo mode without Gemini key</label>
          <button class="warm" type="submit">Run Translation Agents</button>
        </form>
      </section>

      <section class="panel stack">
        <h2>4. Export</h2>
        <form action="/export" method="post">
          <button type="submit">Build Translated Package</button>
        </form>
      </section>
    </aside>

    <div>
      {f'<div class="message">{message}</div>' if message else ''}
      {_status_block()}
      {detail_html}
    </div>
  </main>
</body>
</html>
"""
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return _render()


@app.post("/sample")
def sample() -> HTMLResponse:
    result = runtime.reset_to_sample_book()
    return _render("Sample book loaded. ch02 is ready to translate.", result)


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> HTMLResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".epub":
        return _render("Please upload an .epub file.")
    with NamedTemporaryFile(delete=False, suffix=".epub") as temp:
        temp.write(await file.read())
        temp_path = Path(temp.name)
    try:
        result = runtime.import_epub(temp_path)
        return _render(f"Imported {file.filename}.", result)
    except Exception as exc:
        return _render(f"Import failed: {exc}")
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/analyze")
def analyze() -> HTMLResponse:
    result = run_analysis_workflow()
    return _render("Planner agent analysis complete.", result)


@app.post("/translate-next")
def translate_next(
    target_language: str = Form("Chinese"),
    demo_mode: str | None = Form(None),
) -> HTMLResponse:
    try:
        result = run_translation_workflow(
            target_language=target_language or "Chinese",
            demo_mode=demo_mode == "true",
        )
        translated = result.get("translation", {})
        message = (
            f"Agent workflow translated {translated['chapter_id']} using {translated['mode']} mode."
            if translated.get("ok")
            else translated.get("message", "No chapter translated.")
        )
        return _render(message, result)
    except Exception as exc:
        return _render(f"Translation failed: {exc}")


@app.post("/export")
def export() -> HTMLResponse:
    path = runtime.export_translated_package()
    return _render("Translated package built.", {"download": f"/download/{path.name}"})


@app.get("/download/{filename}")
def download(filename: str):
    safe = Path(filename).name
    path = runtime.EXPORT_DIR / safe
    if not path.exists():
        return RedirectResponse("/")
    return FileResponse(path, media_type="application/zip", filename=safe)
