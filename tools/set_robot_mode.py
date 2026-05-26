from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROBOT_CONFIG_PATH = ROOT / "config" / "robot.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch robot movement mode.")
    parser.add_argument("mode", choices=("dry-run", "real"), help="dry-run logs commands; real moves the arm")
    args = parser.parse_args()

    config = json.loads(ROBOT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["dry_run"] = args.mode == "dry-run"
    ROBOT_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")

    if config["dry_run"]:
        print("Robot mode set to dry-run. The UI will not physically move the arm.")
    else:
        print("Robot mode set to real. The UI will physically move the arm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

