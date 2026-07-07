# How To Use Google SDKs

This project uses two Google-facing layers:

1. **Google ADK** for the multi-agent app.
2. **Gemini API / Google GenAI SDK** for model access in the product
   translation flow and through the ADK agents.

## 1. Install ADK

Google's ADK installation guide recommends a Python virtual environment and
`pip install google-adk`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install google-adk
```

In this project, install everything at once:

```bash
pip install -r requirements.txt
```

## 2. Get A Gemini API Key

Create an API key in Google AI Studio, then put it in `.env`:

```bash
cp .env.example .env
```

`.env`:

```bash
GOOGLE_API_KEY=your-key
TRANSLATIONTRAIL_MODEL=gemini-3.5-flash
```

The Gemini API docs also show direct SDK use with `google-genai`:

```python
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Explain how AI works in a few words",
)
print(response.text)
```

BookWeaver also calls `google-genai` directly in `bookweaver_runtime.py` when
the user clicks the translation button. That makes the product UI visibly use
Gemini for the full-text translation action, while ADK remains responsible for
agent planning and quality checks over bounded MCP tools.

## 3. Run The Product UI

```bash
uvicorn bookweaver_app:app --host 127.0.0.1 --port 7860
```

Open `http://127.0.0.1:7860`.

## 4. Run ADK Web

```bash
adk web
```

Then choose `translationtrail`. Try:

```text
What should I translate next?
Analyze chapter ch02 and recommend a chunking strategy.
Show terms.
Record a decision for ch02: use narrative_heavy because the dialogue ratio is low.
```

## 5. How ADK Connects To MCP

`translationtrail/agent.py` creates `McpToolset` slices. Each slice exposes
only the tools a specialist needs:

- planning agent: read-only progress and chapter analysis
- quality agent: read-only quality checks
- terminology agent: glossary read/write
- memory agent: summary and decision writes

The local MCP server runs over stdio:

```text
ADK LlmAgent -> McpToolset -> python -m mcp_server.server -> sample_workspace metadata
```

This is the key architecture story for the Kaggle writeup.

## Official References

- ADK installation: https://adk.dev/get-started/installation/
- ADK MCP tools: https://adk.dev/tools-custom/mcp-tools/
- Gemini API getting started: https://ai.google.dev/gemini-api/docs/get-started
