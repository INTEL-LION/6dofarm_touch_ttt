from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_PATH = ROOT / "config" / "calibration.json"


def main() -> int:
    data = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    cells = data.get("cells", {})
    errors: list[str] = []

    for cell in range(9):
        cell_data = cells.get(str(cell))
        if not cell_data:
            errors.append(f"cell {cell}: missing")
            continue

        for pose_name in ("approach_pose", "touch_pose"):
            pose = cell_data.get(pose_name)
            if not isinstance(pose, list) or len(pose) != 6:
                errors.append(f"cell {cell} {pose_name}: must contain 6 servo angles")
                continue

            for index, angle in enumerate(pose):
                if not isinstance(angle, int):
                    errors.append(f"cell {cell} {pose_name} servo {index + 1}: not an integer")
                    continue
                upper = 90 if index == 5 else 180
                if angle < 0 or angle > upper:
                    errors.append(
                        f"cell {cell} {pose_name} servo {index + 1}: {angle} outside 0..{upper}"
                    )

    if errors:
        print("Calibration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Calibration validation OK.")
    print("Cells 0-8 all have approach_pose and touch_pose.")
    print("Servo 6 gripper values are within 0..90.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

