# Kaggle Submission Guide

The capstone submission package should contain:

1. Kaggle Writeup
2. Media gallery cover image
3. Attached YouTube video, 5 minutes or less
4. Public project link
5. Optional live demo URL

## Track

Recommended track: **Freestyle**.

Alternative: **Agents for Business**, if you frame it as a professional
translation workflow / localization productivity assistant.

## Public Project Link

Use a public GitHub repository:

```text
https://github.com/<your-user>/bookweaver-studio
```

Before publishing:

```bash
git status
git grep -n "GOOGLE_API_KEY\\|AIza\\|sk-" .
python -m pytest -q
```

Make sure `.env` is not committed.

## Video Checklist

Keep the video under 5 minutes:

1. Problem: long translation projects lose context and terminology.
2. Product workflow:
   - submit/use sample book
   - analyze chapters
   - execute translation
   - export translated package
3. Architecture: BookWeaver product UI + ADK planner/quality agents + MCP tools + Gemini translation.
4. Explain safety:
   - no full-text MCP return
   - full chapter text is translated by the local Gemini runtime, not returned through MCP
   - bounded writes
   - secrets in `.env`
   - audit log
5. Close with deployability: local product UI and optional Cloud Run.

## Writeup Structure

Use `docs/WRITEUP_DRAFT.md` as the starting point. Keep it under the word cap
shown by Kaggle for the competition.

## Kaggle Page Fields

When creating the writeup:

- Title: `TranslationTrail: A Multi-Agent Literary Translation Workspace`
- Subtitle: `Book submission, chapter analysis, Gemini translation, and export with an ADK + MCP agent layer`
- Track: `Freestyle`
- Project link: GitHub repo
- Video: YouTube link
- Cover image: architecture diagram or product screenshot

## Final State Boundary

Do not mark the project as submitted until the Kaggle writeup is actually
created, media is attached, project/video links are attached, and the final
Submit button has been clicked.
