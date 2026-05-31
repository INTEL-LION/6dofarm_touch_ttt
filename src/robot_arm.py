from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from calibration import Calibration, pose_summary


ROOT = Path(__file__).resolve().parents[1]
ROBOT_CONFIG_PATH = ROOT / "config" / "robot.json"
OPEN_GRIPPER_ANGLE = 40.0
CLOSED_GRIPPER_ANGLE = 90.0


@dataclass
class RobotCommandResult:
    cell: int
    dry_run: bool
    message: str


def load_robot_config(path: Path = ROBOT_CONFIG_PATH) -> dict:
    if not path.exists():
        return {
            "mode": "mock",
            "port": "COM3",
            "baud_rate": 9600,
            "timeout_seconds": 2,
            "move_delay_seconds": 0.8,
            "startup_delay_seconds": 2.5,
            "dry_run": True,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def create_robot_arm(config: dict):
    if config.get("mode") == "arduino_serial":
        return ArduinoSerialRobotArm(
            port=config.get("port", "COM3"),
            baud_rate=int(config.get("baud_rate", 9600)),
            timeout_seconds=float(config.get("timeout_seconds", 2)),
            move_delay_seconds=float(config.get("move_delay_seconds", 0.8)),
            startup_delay_seconds=float(config.get("startup_delay_seconds", 2.5)),
        )
    return MockRobotArm()


class MockRobotArm:
    def __init__(self) -> None:
        self.home_pose = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0]

    def touch_cell(
        self,
        cell: int,
        calibration: Calibration,
        dry_run: bool = True,
    ) -> RobotCommandResult:
        if cell not in calibration.cells:
            raise ValueError(f"No calibration pose for cell {cell}")

        pose = calibration.cells[cell]
        mode = "DRY RUN" if dry_run else "MOCK MOVE"
        timestamp = datetime.now().strftime("%H:%M:%S")
        lines = [
            f"[{timestamp}] {mode}: cell {cell}",
            f"home={self.home_pose}",
            f"piece_source={calibration.piece_source}",
            pose_summary(cell, pose),
            "sequence: home -> piece approach -> pick -> lift -> cell approach -> place -> release -> home",
        ]
        return RobotCommandResult(cell=cell, dry_run=dry_run, message="\n".join(lines))


class ArduinoSerialRobotArm:
    def __init__(
        self,
        port: str,
        baud_rate: int = 9600,
        timeout_seconds: float = 2,
        move_delay_seconds: float = 0.8,
        startup_delay_seconds: float = 2.5,
    ) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.timeout_seconds = timeout_seconds
        self.move_delay_seconds = move_delay_seconds
        self.startup_delay_seconds = startup_delay_seconds
        self.home_pose = [90.0, 90.0, 90.0, 90.0, 90.0, 90.0]
        self.connection = None

    def connect(self):
        if self.connection is not None and getattr(self.connection, "is_open", False):
            return self.connection

        serial_module = _load_serial_module()
        connection = serial_module.Serial()
        connection.port = self.port
        connection.baudrate = self.baud_rate
        connection.timeout = self.timeout_seconds

        # Best effort: reduce DTR-triggered auto-reset on compatible adapters.
        # Many Uno/CH340 boards still reset on open because DTR is capacitively
        # wired to RESET, so the more important fix is keeping this connection open.
        try:
            connection.dtr = False
            connection.rts = False
        except Exception:
            pass

        connection.open()
        self.connection = connection
        time.sleep(self.startup_delay_seconds)
        if hasattr(connection, "reset_input_buffer"):
            connection.reset_input_buffer()
        return connection

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def touch_cell(
        self,
        cell: int,
        calibration: Calibration,
        dry_run: bool = True,
    ) -> RobotCommandResult:
        if cell not in calibration.cells:
            raise ValueError(f"No calibration pose for cell {cell}")

        pose = calibration.cells[cell]
        if dry_run and not is_piece_source_ready(calibration):
            timestamp = datetime.now().strftime("%H:%M:%S")
            lines = [
                f"[{timestamp}] ARDUINO SERIAL DRY RUN: cell {cell} on {self.port}",
                "Pick-and-place is enabled, but config/calibration.json piece_source is still empty.",
                "Fill piece_source.approach_pose and piece_source.pick_pose with 6 servo angles each.",
                pose_summary(cell, pose),
            ]
            return RobotCommandResult(cell=cell, dry_run=True, message="\n".join(lines))

        sequence = build_pick_and_place_sequence(
            home_pose=self.home_pose,
            piece_approach_pose=calibration.piece_source.approach_pose,
            piece_pick_pose=calibration.piece_source.pick_pose,
            piece_lift_pose=calibration.piece_source.lift_pose,
            cell_hover_pose=pose.hover_pose,
            cell_approach_pose=pose.approach_pose,
            cell_place_pose=pose.approach_pose,
            cell_exit_pose=pose.exit_pose,
        )

        timestamp = datetime.now().strftime("%H:%M:%S")
        lines = [f"[{timestamp}] ARDUINO SERIAL: cell {cell} on {self.port}"]

        if dry_run:
            for name, angles in sequence:
                lines.append(f"dry-run {name}: {format_servo_command(angles)}")
            return RobotCommandResult(cell=cell, dry_run=True, message="\n".join(lines))

        connection = self.connect()
        ready = _send_command(connection, "PING", "OK PONG")
        lines.append(f"ready: PING -> {ready}")
        angles = _send_command(connection, "Q", "OK ANGLES")
        lines.append(f"current: Q -> {angles}")
        for name, angles in sequence:
            command = format_servo_command(angles)
            response = _send_command(connection, command, "OK MOVE")
            lines.append(f"{name}: {command} -> {response}")
            time.sleep(self.move_delay_seconds)

        return RobotCommandResult(cell=cell, dry_run=False, message="\n".join(lines))


def is_piece_source_ready(calibration: Calibration) -> bool:
    return (
        len(calibration.piece_source.approach_pose) == 6
        and len(calibration.piece_source.pick_pose) == 6
    )


def build_pick_and_place_sequence(
    home_pose: list[float],
    piece_approach_pose: list[float],
    piece_pick_pose: list[float],
    piece_lift_pose: list[float],
    cell_hover_pose: list[float],
    cell_approach_pose: list[float],
    cell_place_pose: list[float],
    cell_exit_pose: list[float],
) -> list[tuple[str, list[float]]]:
    _validate_pose("piece_source.approach_pose", piece_approach_pose)
    _validate_pose("piece_source.pick_pose", piece_pick_pose)
    if piece_lift_pose:
        _validate_pose("piece_source.lift_pose", piece_lift_pose)
    else:
        piece_lift_pose = piece_approach_pose
    if cell_hover_pose:
        _validate_pose("cell.hover_pose", cell_hover_pose)
    else:
        cell_hover_pose = cell_approach_pose
    if cell_exit_pose:
        _validate_pose("cell.exit_pose", cell_exit_pose)
    else:
        cell_exit_pose = cell_hover_pose
    _validate_pose("cell.approach_pose", cell_approach_pose)
    _validate_pose("cell.place_pose", cell_place_pose)

    return [
        ("home", home_pose),
        ("piece approach open", with_gripper(piece_approach_pose, OPEN_GRIPPER_ANGLE)),
        ("piece pick open", with_gripper(piece_pick_pose, OPEN_GRIPPER_ANGLE)),
        ("piece pick close", with_gripper(piece_pick_pose, CLOSED_GRIPPER_ANGLE)),
        ("piece lift", with_gripper(piece_lift_pose, CLOSED_GRIPPER_ANGLE)),
        ("cell hover holding", with_gripper(cell_hover_pose, CLOSED_GRIPPER_ANGLE)),
        ("cell approach holding", with_gripper(cell_approach_pose, CLOSED_GRIPPER_ANGLE)),
        ("cell place holding", with_gripper(cell_place_pose, CLOSED_GRIPPER_ANGLE)),
        ("cell release", with_gripper(cell_place_pose, OPEN_GRIPPER_ANGLE)),
        ("cell vertical lift open", with_gripper(cell_exit_pose, OPEN_GRIPPER_ANGLE)),
        ("home", home_pose),
    ]


def with_gripper(pose: list[float], gripper_angle: float) -> list[float]:
    _validate_pose("pose", pose)
    updated = pose.copy()
    updated[5] = gripper_angle
    return updated


def _validate_pose(name: str, pose: list[float]) -> None:
    if len(pose) != 6:
        raise ValueError(
            f"{name} must contain 6 servo angles. "
            "Fill config/calibration.json piece_source before real pick-and-place."
        )


def format_servo_command(angles: list[float]) -> str:
    if len(angles) != 6:
        raise ValueError(f"Expected 6 servo angles, got {len(angles)}")
    bounded = [_clamp_angle(index, angle) for index, angle in enumerate(angles)]
    return "M " + ",".join(str(angle) for angle in bounded)


def _clamp_angle(index: int, angle: float) -> int:
    value = int(round(angle))
    lower = 0
    upper = 90 if index == 5 else 180
    return max(lower, min(upper, value))


def _load_serial_module():
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial is required for Arduino serial mode. Install it with: python -m pip install pyserial") from exc
    return serial


def _send_command(connection, command: str, expected_prefix: str = "OK") -> str:
    connection.write((command + "\n").encode("ascii"))
    deadline = time.time() + 5.0

    while time.time() < deadline:
        response = connection.readline().decode("ascii", errors="replace").strip()
        if not response:
            continue
        if response == "OK READY":
            continue
        if response.startswith(expected_prefix):
            return response
        if response.startswith("ERR"):
            raise RuntimeError(f"Arduino rejected command {command}: {response}")

    raise RuntimeError(f"No matching Arduino response after command: {command}")
