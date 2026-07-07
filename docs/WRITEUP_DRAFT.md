# BookWeaver Studio: A Local AI Translation Workspace

## Subtitle

Book submission, chapter analysis, Gemini translation, and export with an ADK +
MCP agent layer.

## Problem

Long-form translation is not just sentence-by-sentence translation. A human
translator needs continuity across chapters: names must stay consistent,
chapter summaries must survive across sessions, and every translated file needs
basic quality checks. When a project spans dozens of chapters, ordinary chat
interfaces lose structure and make it too easy to paste too much text into a
model prompt.

## Solution

BookWeaver Studio is a local web app for managing literary translation projects.
The user can submit an EPUB, analyze chapters, translate the next pending
chapter with Gemini, and export a translated package.

Behind the product UI, a Google ADK coordinator is used for agent reasoning and
tool use. The UI calls ADK for planning before translation and quality checking
after translation. The full chapter translation itself is executed by the local
runtime with Gemini, because the MCP boundary intentionally does not expose full
chapter text to LLM agents.

The ADK app contains four specialists:

- `planning_agent` checks progress and recommends the next chapter and chunking
  strategy.
- `terminology_agent` maintains names, places, and special terms.
- `memory_agent` records bounded chapter summaries and translation decisions.
- `quality_agent` checks translated chapter availability and structure.

The agents use Gemini for reasoning and communicate with a local MCP server for
workspace operations. The MCP server provides a fixed tool surface over a sample
EPUB-like workspace. It returns metadata, statistics, glossary entries, bounded
summaries, and structural quality results. It intentionally does not return full
chapter text.

## Architecture

The architecture is built around a clear boundary:

```text
BookWeaver product UI
        |
        +--> ADK root_agent + Gemini reasoning
        |         |
        |         v
        |     MCP server over stdio
        |         |
        |         v
        |     sample_workspace metadata and quality status
        |
        +--> local runtime + google-genai for full chapter translation
```

This design separates agent reasoning from deterministic file operations. It
also supports least privilege: planning and quality agents use read-only tools,
while terminology and memory agents have only bounded metadata-write tools.

## Course Concepts Demonstrated

TranslationTrail demonstrates at least three course concepts:

1. **Google ADK multi-agent system**: a coordinator plus four specialized agents.
2. **MCP server**: a local stdio server exposes tools for project status,
   chapter analysis, glossary, memory, and quality checks.
3. **Gemini API**: used by ADK agents for reasoning and by the product runtime
   for the visible chapter translation action.
4. **Security features**: no full-text MCP return, safe chapter ID validation,
   bounded writes, no committed secrets, and an MCP audit log.

It also demonstrates deployability through ADK Web locally and documented Cloud
Run deployment.

## Demo

In the demo, I use the product UI. First I load the sample book and run ADK
planner analysis. The returned trace shows the coordinator transferring the
request to `planning_agent`, which calls MCP tools such as `get_project_status`,
`list_chapters`, and `analyze_chapter`.

Next, I run the translation action. The product runtime calls Gemini to translate
the next pending chapter. After the translated file is written, the UI runs ADK
quality analysis, where `quality_agent` calls MCP tools such as
`get_quality_status` and `list_chapters`. Finally, I export the translated
package.

## Impact

The project is useful because it treats translation as a long-running workflow
rather than a single prompt. The agent does not replace the human translator; it
keeps the project organized, remembers decisions, protects context boundaries,
and makes quality review easier.

## Limitations And Next Steps

This Kaggle version uses fabricated sample text. A production version would add
richer EPUB reconstruction, bilingual diff review, authenticated storage, and a
human approval step for all persistent writes.
