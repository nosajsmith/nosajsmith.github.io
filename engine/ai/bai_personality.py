from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping

from .bai_doctrine import build_doctrine_profile, derive_behavior_values


def apply_personality_overlay(
    base_profile: Mapping[str, Any] | None,
    engine_config: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    config = dict(engine_config or {})
    personality = dict(config.get("personality") or {})

    profile = deepcopy(dict(base_profile or build_doctrine_profile(config)))
    profile.setdefault("axis", {})
    profile.setdefault("run", {})
    profile.setdefault("metadata", {})
    profile.setdefault("profile_selection", {})
    profile.setdefault("sources", {})
    profile.setdefault("warnings", [])

    personality_axis = personality.get("axis")
    personality_run = personality.get("run")
    personality_metadata = personality.get("metadata")

    if isinstance(personality_axis, Mapping):
        profile["axis"].update(dict(personality_axis))
    if isinstance(personality_run, Mapping):
        profile["run"].update(dict(personality_run))
    if isinstance(personality_metadata, Mapping):
        profile["metadata"].update(dict(personality_metadata))

    if isinstance(config.get("axis"), Mapping):
        profile["axis"].update(dict(config.get("axis") or {}))
    if isinstance(config.get("run"), Mapping):
        profile["run"].update(dict(config.get("run") or {}))
    if isinstance(config.get("metadata"), Mapping):
        profile["metadata"].update(dict(config.get("metadata") or {}))
    if isinstance(config.get("profile_selection"), Mapping):
        profile["profile_selection"] = dict(config.get("profile_selection") or {})

    profile["sources"] = {
        **dict(profile.get("sources") or {}),
        "personality": bool(personality),
        "runtime_overrides": bool(config.get("axis") or config.get("run")),
    }

    normalized_doctrine = build_doctrine_profile(
        {
            "doctrine": {
                "axis": profile.get("axis"),
                "run": profile.get("run"),
                "metadata": profile.get("metadata"),
            },
            "profile_selection": profile.get("profile_selection"),
        }
    )
    normalized_doctrine["sources"] = profile["sources"]
    normalized_doctrine["warnings"] = list(profile.get("warnings") or [])
    return normalized_doctrine


def build_runtime_behavior_profile(engine_config: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    profile = build_doctrine_profile(engine_config)
    merged = apply_personality_overlay(profile, engine_config)
    merged.update(derive_behavior_values(merged["axis"], merged["run"]))
    return merged


__all__ = ["apply_personality_overlay", "build_runtime_behavior_profile"]
