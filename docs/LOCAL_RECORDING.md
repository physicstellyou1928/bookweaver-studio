# Local Recording Checklist

Use this when recording the Kaggle demo video. The main video should show the
BookWeaver product UI, because it has visible upload/analyze/translate/export
controls. ADK Web is optional supporting evidence.

## 1. Start The App

```bash
cd bookweaver-studio
source .venv/bin/activate
uvicorn bookweaver_app:app --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860
```

Use the four visible panels:

1. Submit A Book
2. Analyze
3. Execute Translation
4. Export

## 2. Before Recording

Make sure `.env` has a real Gemini key:

```bash
GOOGLE_API_KEY=replace-with-your-gemini-api-key
TRANSLATIONTRAIL_MODEL=gemini-3.5-flash
TRANSLATIONTRAIL_WORKSPACE=sample_workspace
TRANSLATIONTRAIL_CONFIRM_WRITES=FALSE
```

Do not commit `.env`.

If you do not want to spend API calls during rehearsal, check `demo mode without
Gemini key` in the UI. For the final video, a real Gemini translation is better.

## 3. Demo Flow

Use these actions in order:

1. Click `Use Sample Book`.
2. Click `Analyze Book`.
3. Under `Execute Translation`, keep target language as `Chinese`.
4. Click `Translate Next Chapter`.
5. Click `Build Translated Package`.
6. Open the generated download link if you want to show the exported ZIP.

## 4. Optional ADK Debug View

You can also show the ADK graph briefly:

```bash
adk web --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/dev-ui/` and choose `translationtrail`.

## 5. What To Say

- This is a Google ADK multi-agent app.
- Gemini powers the specialist agents.
- MCP exposes local tools for status, glossary, memory and quality checks.
- The product UI executes the visible translation workflow.
- The MCP server does not return full chapter text to the agents, only metadata and metrics.
- The sample workspace is fabricated so the GitHub/Kaggle submission is safe.
