from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from calibration import load_calibration  # noqa: E402
from robot_arm import create_robot_arm, load_robot_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Touch one calibrated tic-tac-toe cell.")
    parser.add_argument("cell", type=int, choices=range(9), help="Cell number 0-8")
    parser.add_argument("--real", action="store_true", help="Actually move the Arduino arm")
    parser.add_argument(
        "--allow-reset-risk",
        action="store_true",
        help="Allow one-shot real movement even though opening the serial port may reset the Uno",
    )
    args = parser.parse_args()

    config = load_robot_config()
    calibration = load_calibration()
    robot = create_robot_arm(config)
    dry_run = not args.real

    if args.real and not args.allow_reset_risk:
        print("Blocked one-shot real movement.")
        print("Reason: opening the serial port can reset the Uno, briefly stopping servo PWM.")
        print("Use tools/touch_cell_session.py or the game UI Connect Robot button instead.")
        print("If you fully understand the reset risk, pass --allow-reset-risk.")
        return 2

    result = robot.touch_cell(args.cell, calibration, dry_run=dry_run)
    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
