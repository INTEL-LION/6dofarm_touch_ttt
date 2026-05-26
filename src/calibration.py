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


def load_calibration(path: Path = CALIBRATION_PATH) -> dict[int, CellPose]:
    if not path.exists():
        path = EXAMPLE_PATH

    data = json.loads(path.read_text(encoding="utf-8"))
    calibration: dict[int, CellPose] = {}

    for key, value in data["cells"].items():
        cell = int(key)
        calibration[cell] = CellPose(
            approach_pose=[float(item) for item in value["approach_pose"]],
            touch_pose=[float(item) for item in value["touch_pose"]],
        )

    missing = set(range(9)) - set(calibration)
    if missing:
        raise ValueError(f"Calibration is missing cells: {sorted(missing)}")

    return calibration


def pose_summary(cell: int, pose: CellPose) -> str:
    return (
        f"cell {cell}: approach={_fmt_pose(pose.approach_pose)}, "
        f"touch={_fmt_pose(pose.touch_pose)}"
    )


def _fmt_pose(values: list[float]) -> str:
    return "[" + ", ".join(f"{value:.1f}" for value in values) + "]"

