from __future__ import annotations

from typing import Any


def render_regression_report(comparison: Any | None) -> str:
    if not comparison:
        return "No regression comparison requested."
    return f"Regression comparison:\n{comparison}"

