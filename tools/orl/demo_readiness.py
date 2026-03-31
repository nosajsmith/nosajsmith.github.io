from __future__ import annotations

import json
import sys
from pathlib import Path


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from engine.testing_api import EngineTestingAPI


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    command = args[0] if args else "deterministic-demo"
    scenario_name = args[1] if len(args) > 1 else ""
    api = EngineTestingAPI()

    if command == "checklist":
        result = api.demo_checklist(scenario_name=scenario_name)
    elif command == "deterministic-demo":
        result = api.deterministic_demo_runner(scenario_name=scenario_name)
    elif command == "latest-artifacts":
        result = api.latest_artifacts()
    elif command == "validate-artifacts":
        result = api.demo_artifact_validation()
    else:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"Unsupported command: {command}",
                    "supported": [
                        "checklist",
                        "deterministic-demo",
                        "latest-artifacts",
                        "validate-artifacts",
                    ],
                },
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": result.ok,
                "adapter_method": result.adapter_method,
                "error": result.error,
                "artifacts": result.artifacts,
                "metrics": result.metrics,
                "data": result.data,
                "logs": result.logs,
            },
            indent=2,
        )
    )
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
