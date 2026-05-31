from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
CALIBRATION_PATH = CONFIG_DIR / "calibration.json"
EXAMPLE_PATH = CONFIG_DIR / "calibration.example.json"


@dataclass(frozen=True)
class CellPose:
    approach_pose: list[float]
    touch_pose: list[float]
    hover_pose: list[float]
    exit_pose: list[float]
    clear_pose: list[float]


@dataclass(frozen=True)
class PieceSourcePose:
    approach_pose: list[float]
    pick_pose: list[float]
    lift_pose: list[float]


@dataclass(frozen=True)
class Calibration:
    cells: dict[int, CellPose]
    piece_source: PieceSourcePose


def load_calibration(path: Path = CALIBRATION_PATH) -> Calibration:
    if not path.exists():
        path = EXAMPLE_PATH

    data = json.loads(path.read_text(encoding="utf-8"))
    calibration: dict[int, CellPose] = {}

    for key, value in data["cells"].items():
        cell = int(key)
        calibration[cell] = CellPose(
            approach_pose=[float(item) for item in value["approach_pose"]],
            touch_pose=[float(item) for item in value["touch_pose"]],
            hover_pose=[float(item) for item in value.get("hover_pose", [])],
            exit_pose=[float(item) for item in value.get("exit_pose", [])],
            clear_pose=[float(item) for item in value.get("clear_pose", [])],
        )

    missing = set(range(9)) - set(calibration)
    if missing:
        raise ValueError(f"Calibration is missing cells: {sorted(missing)}")

    piece_source_data = data.get("piece_source", {})
    piece_source = PieceSourcePose(
        approach_pose=[float(item) for item in piece_source_data.get("approach_pose", [])],
        pick_pose=[float(item) for item in piece_source_data.get("pick_pose", [])],
        lift_pose=[float(item) for item in piece_source_data.get("lift_pose", [])],
    )

    return Calibration(cells=calibration, piece_source=piece_source)


def pose_summary(cell: int, pose: CellPose) -> str:
    return (
        f"cell {cell}: approach={_fmt_pose(pose.approach_pose)}, "
        f"touch={_fmt_pose(pose.touch_pose)}, hover={_fmt_pose(pose.hover_pose)}, "
        f"exit={_fmt_pose(pose.exit_pose)}, clear={_fmt_pose(pose.clear_pose)}"
    )


def _fmt_pose(values: list[float]) -> str:
    return "[" + ", ".join(f"{value:.1f}" for value in values) + "]"
