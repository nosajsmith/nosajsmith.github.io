from __future__ import annotations

import json
from pathlib import Path

from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.manifest import build_manifest_record, write_manifest
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.runners import execute_single_run


ROOT = Path(__file__).resolve().parents[1]


def test_bai_warlab_manifest_records_rerun_metadata(tmp_path: Path):
    loader = ConfigLoader(ROOT / "configs" / "ai")
    argv = [
        "run",
        "--scenario",
        "mini_gc_1942",
        "--scenario-dir",
        "scenarios",
        "--doctrine",
        "korea_nkpa_shock",
        "--personality",
        "aggressive",
        "--tuning",
        "default",
        "--seed",
        "7",
    ]
    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=7,
            max_steps=2,
        ),
        loader,
    )

    manifest = build_manifest_record(
        command="run",
        output_dir=tmp_path,
        scenario="mini_gc_1942",
        doctrine="korea_nkpa_shock",
        personality="aggressive",
        tuning="default",
        seed_policy={"kind": "explicit", "seeds": [7]},
        command_line=" ".join(argv),
        command_argv=argv,
        config_root=ROOT / "configs" / "ai",
        loader=loader,
        result=result,
    )
    path = write_manifest(tmp_path / "manifest.json", manifest)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["bai_version"]
    assert payload["extra"]["rerun"]["argv"][0] == "run"
    assert payload["extra"]["scenario_records"][0]["scenario_id"] == "mini_gc_1942"
    assert payload["extra"]["scenario_records"][0]["source_path"].endswith("mini_gc_1942.json")
    assert len(payload["extra"]["scenario_records"][0]["sha256"]) == 64
    assert payload["extra"]["profile_records"]["doctrine"]["source_path"].endswith("korea_nkpa_shock.yaml")
    assert len(payload["extra"]["profile_records"]["doctrine"]["sha256"]) == 64
    assert payload["extra"]["profile_records"]["personality"]["selector"] == "aggressive"
    assert payload["extra"]["profile_records"]["personality"]["source_path"].endswith("aggressive.yaml")
    assert payload["extra"]["profile_records"]["tuning"]["source_path"].endswith("default.yaml")
