# Demo Video Script

Target length: 3-5 minutes.

## 0:00 - 0:30 Problem

"TranslationTrail solves a long-form translation workflow problem. Translators
need consistent names, persistent context, quality checks, and safe tool use
across many chapters."

## 0:30 - 1:15 Architecture

Show README architecture diagram.

"The app uses Google ADK with one coordinator and four specialist agents:
planning, terminology, memory, and quality. Gemini powers the reasoning. A local
MCP server exposes the workspace tools."

"The product UI calls ADK for planning and quality checks. Full chapter
translation is handled by the local runtime with Gemini, because the MCP tools
intentionally do not expose full chapter text to agents."

Point out:

- ADK: `translationtrail/agent.py`
- UI to ADK bridge: `bookweaver_adk.py`
- MCP: `mcp_server/server.py`
- Deterministic store: `mcp_server/store.py`

## 1:15 - 3:45 Live Demo

Start:

```bash
uvicorn bookweaver_app:app --host 127.0.0.1 --port 7860
```

Open `http://127.0.0.1:7860`.

Show the four product panels:

1. Submit A Book
2. Analyze
3. Execute Translation
4. Export

Click:

- `Use Sample Book`
- `Run ADK Planner`
- Show `adk_planning.events`: transfer to `planning_agent`, then MCP tool calls
- `Run Gemini Translation + Quality Agent`
- Show `mode: gemini` and `adk_quality.events`
- `Build Translated Package`

Say:

"This is not only an agent graph. The app has a concrete book workflow: submit
an EPUB, analyze chapters, execute translation, and export translated output."

"The important implementation detail is honest separation. ADK agents reason
over bounded metadata through MCP. The full text translation is a local Gemini
runtime action, so the agent tool layer does not leak whole chapters."

## 3:30 - 4:30 Safety

"The important safety design is that MCP does not return full chapter text. It
returns metadata, statistics, bounded summaries, and quality metrics. Writes are
limited to glossary, summaries, and decision records."

Show `.env.example` and `.gitignore`.

## 4:30 - 5:00 Deployment

"The app runs locally with ADK Web and can be deployed to Cloud Run with ADK's
Cloud Run deploy command. The repository includes deployment and Kaggle
submission docs."
