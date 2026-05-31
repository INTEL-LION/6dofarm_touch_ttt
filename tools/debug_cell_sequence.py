from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from calibration import load_calibration  # noqa: E402
from robot_arm import (  # noqa: E402
    ArduinoSerialRobotArm,
    build_pick_and_place_sequence,
    create_robot_arm,
    format_servo_command,
    load_robot_config,
    with_gripper,
    OPEN_GRIPPER_ANGLE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Step through one cell's pick-and-place sequence.")
    parser.add_argument("cell", type=int, choices=range(9), help="Cell number 0-8")
    parser.add_argument("--real", action="store_true", help="Send each step to Arduino after confirmation")
    args = parser.parse_args()

    config = load_robot_config()
    calibration = load_calibration()
    pose = calibration.cells[args.cell]
    robot = create_robot_arm(config)

    sequence = build_pick_and_place_sequence(
        home_pose=[90.0, 90.0, 90.0, 90.0, 90.0, 90.0],
        piece_approach_pose=calibration.piece_source.approach_pose,
        piece_pick_pose=calibration.piece_source.pick_pose,
        piece_lift_pose=calibration.piece_source.lift_pose,
        cell_hover_pose=pose.hover_pose,
        cell_approach_pose=pose.approach_pose,
        cell_place_pose=pose.approach_pose,
        cell_exit_pose=pose.exit_pose,
        cell_clear_pose=pose.clear_pose,
    )

    print(f"Debugging cell {args.cell}")
    print("Focus on transitions after 'cell release'.")
    print("If the arm hits the ring before 'cell clear open', recalibrate exit_pose.")
    print("If the arm hits the ring after 'cell clear open', recalibrate clear_pose higher/safer.")
    print("")

    if args.real and not isinstance(robot, ArduinoSerialRobotArm):
        print("Real debug requires arduino_serial mode.")
        return 1

    connection = None
    try:
        if args.real:
            print("Opening persistent Arduino connection.")
            print("Support the arm during the first connection reset.")
            connection = robot.connect()

        previous: list[float] | None = None
        for index, (name, angles) in enumerate(sequence, start=1):
            command = format_servo_command(angles)
            print(f"{index:02d}. {name}: {command}")
            if previous is not None:
                print("    delta:", _delta(previous, angles))
            _warn_if_post_release_twist(sequence, index, previous, angles)

            if args.real:
                answer = input("    Press Enter to send, s to skip, q to quit: ").strip().lower()
                if answer == "q":
                    break
                if answer == "s":
                    previous = angles
                    continue
                response = _send_move(connection, command)
                print(f"    {response}")
                time.sleep(float(config.get("move_delay_seconds", 1.1)))

            previous = angles
    finally:
        if args.real and hasattr(robot, "close"):
            robot.close()

    print("")
    print("For top-row cells 0/1/2, release -> exit -> clear should keep the base angle fixed.")
    print("Use the calibrator to save a safer Clear Pose if home rotation still hits the ring.")
    return 0


def _send_move(connection, command: str) -> str:
    connection.write((command + "\n").encode("ascii"))
    deadline = time.time() + 10.0
    while time.time() < deadline:
        response = connection.readline().decode("ascii", errors="replace").strip()
        if response.startswith("OK MOVE"):
            return response
        if response.startswith("ERR"):
            raise RuntimeError(response)
    raise RuntimeError(f"No OK MOVE response after {command}")


def _delta(previous: list[float], current: list[float]) -> str:
    values = [int(round(c - p)) for p, c in zip(previous, current)]
    return "[" + ", ".join(f"{value:+d}" for value in values) + "]"


def _warn_if_post_release_twist(
    sequence: list[tuple[str, list[float]]],
    index: int,
    previous: list[float] | None,
    current: list[float],
) -> None:
    if previous is None:
        return
    previous_name = sequence[index - 2][0]
    current_name = sequence[index - 1][0]
    if previous_name.startswith("cell release") or previous_name.startswith("cell vertical"):
        base_delta = abs(current[0] - previous[0])
        if base_delta > 2 and not current_name.startswith("home"):
            print(f"    WARNING: base changes by {base_delta:.1f} near the ring.")
        if current_name.startswith("home") and base_delta > 2:
            print("    NOTE: base rotates toward home. clear_pose must be high enough before this step.")


if __name__ == "__main__":
    raise SystemExit(main())
