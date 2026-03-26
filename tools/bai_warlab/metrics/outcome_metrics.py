from __future__ import annotations

from typing import Any, Dict


SIDES = ("ALLIED", "AXIS")


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _perspective_result(winning_side: str | None, side: str) -> str:
    if not winning_side:
        return "draw"
    return "win" if side == winning_side else "loss"


def compute_outcome_metrics(context: Dict[str, Any]) -> Dict[str, Any]:
    vp = dict(context.get("vp") or {})
    winning_side = str(context.get("winning_side") or "").strip().upper() or None
    scenario_outcome = str(context.get("scenario_outcome") or "unknown")
    steps_completed = _to_int(context.get("steps_completed"))
    max_steps_exhausted = bool(context.get("max_steps_exhausted", False))

    allied_vp = _to_int(vp.get("ALLIED"))
    axis_vp = _to_int(vp.get("AXIS"))
    vp_margin_allied = allied_vp - axis_vp
    vp_margin_axis = axis_vp - allied_vp

    return {
        "available": True,
        "scenario_outcome": scenario_outcome,
        "winning_side": winning_side or "",
        "win_loss_draw_allied": _perspective_result(winning_side, "ALLIED"),
        "win_loss_draw_axis": _perspective_result(winning_side, "AXIS"),
        "vp_allied": allied_vp,
        "vp_axis": axis_vp,
        "vp_margin_allied": vp_margin_allied,
        "vp_margin_axis": vp_margin_axis,
        "absolute_vp_margin": abs(vp_margin_allied),
        "steps_completed": steps_completed,
        "max_steps_exhausted": max_steps_exhausted,
    }


__all__ = ["compute_outcome_metrics"]
