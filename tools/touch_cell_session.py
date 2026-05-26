from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from calibration import load_calibration  # noqa: E402
from robot_arm import create_robot_arm, load_robot_config  # noqa: E402


def main() -> int:
    config = load_robot_config()
    calibration = load_calibration()
    robot = create_robot_arm(config)

    if config.get("dry_run", True):
        print("robot.json is still dry_run=true.")
        print("Run .\\run_mode_real.bat first if you want physical movement.")
        return 1

    print("Opening one persistent Arduino connection.")
    print("The first connection may still reset the Uno once; after that, keep this window open.")
    print("Enter a cell number 0-8, or q to quit.")

    try:
        if hasattr(robot, "connect"):
            robot.connect()
            print("Connected. Servos should now remain under continuous Arduino control.")

        while True:
            raw = input("cell> ").strip().lower()
            if raw in {"q", "quit", "exit"}:
                break
            if not raw.isdigit() or int(raw) not in range(9):
                print("Enter 0-8 or q.")
                continue

            result = robot.touch_cell(int(raw), calibration, dry_run=False)
            print(result.message)
    finally:
        if hasattr(robot, "close"):
            robot.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

