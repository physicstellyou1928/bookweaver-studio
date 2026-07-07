"""Runtime configuration for the TranslationTrail ADK app."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.environ.get("TRANSLATIONTRAIL_WORKSPACE", "sample_workspace"))
MODEL = os.environ.get("TRANSLATIONTRAIL_MODEL", "gemini-3.5-flash")

