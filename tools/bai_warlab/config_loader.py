from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

from . import CONFIG_ROOT
from .models import ProfileDocument, ResolvedProfiles


class BAIWarLabConfigError(ValueError):
    pass


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


class ConfigLoader:
    def __init__(self, config_root: str | Path | None = None):
        self.config_root = Path(config_root or CONFIG_ROOT).resolve()

    def _resolve_profile_path(self, group: str, name_or_path: str) -> Path:
        candidate = Path(name_or_path)
        if candidate.suffix in {".yaml", ".yml"} and candidate.exists():
            return candidate.resolve()

        yaml_path = self.config_root / group / f"{name_or_path}.yaml"
        if yaml_path.exists():
            return yaml_path.resolve()

        yml_path = self.config_root / group / f"{name_or_path}.yml"
        if yml_path.exists():
            return yml_path.resolve()

        raise BAIWarLabConfigError(f"Missing {group} profile: {name_or_path}")

    def _load_profile(self, group: str, name_or_path: str) -> ProfileDocument:
        path = self._resolve_profile_path(group, name_or_path)
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise BAIWarLabConfigError(f"Profile at {path} must load as a mapping")

        axis = payload.get("axis") or {}
        run = payload.get("run") or {}
        metadata = payload.get("metadata") or {}
        if not isinstance(axis, dict):
            raise BAIWarLabConfigError(f"Profile {path.stem} axis block must be a mapping")
        if not isinstance(run, dict):
            raise BAIWarLabConfigError(f"Profile {path.stem} run block must be a mapping")
        if not isinstance(metadata, dict):
            raise BAIWarLabConfigError(f"Profile {path.stem} metadata block must be a mapping")

        return ProfileDocument(
            kind=group,
            name=str(payload.get("name") or path.stem),
            description=str(payload.get("description") or ""),
            axis=deepcopy(axis),
            run=deepcopy(run),
            metadata=deepcopy(metadata),
            source_path=str(path),
        )

    def load_doctrine(self, name_or_path: str) -> ProfileDocument:
        return self._load_profile("doctrines", name_or_path)

    def load_personality(self, name_or_path: str) -> ProfileDocument:
        return self._load_profile("personalities", name_or_path)

    def load_tuning(self, name_or_path: str) -> ProfileDocument:
        return self._load_profile("tuning", name_or_path)

    def resolve_profiles(self, doctrine: str, personality: str, tuning: str) -> ResolvedProfiles:
        doctrine_doc = self.load_doctrine(doctrine)
        personality_doc = self.load_personality(personality)
        tuning_doc = self.load_tuning(tuning)

        merged_axis = _deep_merge(doctrine_doc.axis, personality_doc.axis)
        merged_axis = _deep_merge(merged_axis, tuning_doc.axis)

        merged_run = _deep_merge(doctrine_doc.run, personality_doc.run)
        merged_run = _deep_merge(merged_run, tuning_doc.run)

        warnings = []
        if "aggression" not in merged_axis:
            warnings.append("Merged profile does not define axis.aggression; scenario defaults will apply later.")

        return ResolvedProfiles(
            doctrine=doctrine_doc,
            personality=personality_doc,
            tuning=tuning_doc,
            merged_axis=merged_axis,
            merged_run=merged_run,
            warnings=warnings,
        )

