from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BAG_ROOT = ROOT / "bags"
INVALID_PATH_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
TOPIC_SERVO_ANGLES = "/robot_arm/target_servo_angles"
TOPIC_SEQUENCE_STEP = "/robot_arm/sequence_step"
TOPIC_GAME_STATE = "/ttt/game_state"
TOPIC_RECOMMENDED_MOVE = "/ttt/recommended_move"
TOPIC_EVENT = "/robot_arm/event"


@dataclass
class BagPaths:
    directory: Path
    events_jsonl: Path
    servo_csv: Path
    analysis_html: Path


class SessionBagRecorder:
    def __init__(self, root: Path = BAG_ROOT) -> None:
        self.root = root
        self.paths: BagPaths | None = None
        self.enabled = False
        self._step_index = 0

    def start(self, name: str | None = None) -> BagPaths:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = unique_bag_directory(self.root, name or f"v1_3_bag_{stamp}")
        directory.mkdir(parents=True, exist_ok=True)
        self.paths = BagPaths(
            directory=directory,
            events_jsonl=directory / "events.jsonl",
            servo_csv=directory / "servo_steps.csv",
            analysis_html=directory / "analysis.html",
        )
        self.enabled = True
        self._step_index = 0
        self._write_servo_header()
        self.record_event(TOPIC_EVENT, {"event": "bag_started", "version": "v1.3"})
        return self.paths

    def stop(self) -> BagPaths | None:
        if not self.paths:
            self.enabled = False
            return None
        self.record_event(TOPIC_EVENT, {"event": "bag_stopped", "version": "v1.3"})
        self.enabled = False
        self.write_analysis()
        return self.paths

    def record_event(self, topic: str, data: dict[str, Any]) -> None:
        if not self.enabled or not self.paths:
            return
        event = {
            "time": time.time(),
            "topic": topic,
            "data": data,
        }
        with self.paths.events_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def record_game_state(self, board: list[str], turn: str, note: str = "") -> None:
        self.record_event(TOPIC_GAME_STATE, {"board": board.copy(), "turn": turn, "note": note})

    def record_recommended_move(self, cell: int | None, analyses: dict[int, Any]) -> None:
        payload = {
            "cell": cell,
            "analyses": {
                str(key): {
                    "score": value.score,
                    "category": value.category,
                    "label": value.label,
                    "is_best": value.is_best,
                }
                for key, value in analyses.items()
            },
        }
        self.record_event(TOPIC_RECOMMENDED_MOVE, payload)

    def record_robot_steps(self, cell: int, steps: list[dict[str, Any]], result_message: str = "") -> None:
        if not self.enabled or not self.paths:
            return
        for step in steps:
            self._step_index += 1
            name = str(step.get("name", ""))
            angles = [float(item) for item in step.get("angles", [])]
            speed = int(step.get("speed_percent", 100))
            dry_run = bool(step.get("dry_run", False))
            self.record_event(
                TOPIC_SEQUENCE_STEP,
                {
                    "index": self._step_index,
                    "cell": cell,
                    "name": name,
                    "speed_percent": speed,
                    "dry_run": dry_run,
                },
            )
            self.record_event(
                TOPIC_SERVO_ANGLES,
                {
                    "index": self._step_index,
                    "cell": cell,
                    "name": name,
                    "speed_percent": speed,
                    "angles": angles,
                },
            )
            self._append_servo_row(self._step_index, cell, name, speed, angles, dry_run)
        if result_message:
            self.record_event(TOPIC_EVENT, {"event": "robot_result", "cell": cell, "message": result_message})

    def write_analysis(self) -> Path | None:
        if not self.paths:
            return None
        rows = self._read_servo_rows()
        html = build_analysis_html(rows, self.paths.directory.name)
        self.paths.analysis_html.write_text(html, encoding="utf-8")
        return self.paths.analysis_html

    def open_analysis(self) -> Path | None:
        return self.write_analysis()

    def set_root(self, root: Path) -> None:
        self.root = root

    def _write_servo_header(self) -> None:
        if not self.paths:
            return
        with self.paths.servo_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "step",
                    "cell",
                    "name",
                    "speed_percent",
                    "servo1",
                    "servo2",
                    "servo3",
                    "servo4",
                    "servo5",
                    "servo6_gripper",
                    "dry_run",
                ]
            )

    def _append_servo_row(
        self,
        step: int,
        cell: int,
        name: str,
        speed: int,
        angles: list[float],
        dry_run: bool,
    ) -> None:
        if not self.paths:
            return
        with self.paths.servo_csv.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([step, cell, name, speed, *angles, dry_run])

    def _read_servo_rows(self) -> list[dict[str, str]]:
        if not self.paths or not self.paths.servo_csv.exists():
            return []
        with self.paths.servo_csv.open("r", newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


def sanitize_bag_name(name: str) -> str:
    clean = re.sub(INVALID_PATH_CHARS, "_", name).strip()
    clean = re.sub(r"\s+", "_", clean)
    clean = clean.strip("._ ")
    return clean or datetime.now().strftime("v1_3_bag_%Y%m%d_%H%M%S")


def unique_bag_directory(root: Path, name: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    base = sanitize_bag_name(name)
    candidate = root / base
    suffix = 2
    while candidate.exists():
        candidate = root / f"{base}_{suffix}"
        suffix += 1
    return candidate


def list_bag_directories(root: Path = BAG_ROOT) -> list[Path]:
    if not root.exists():
        return []
    bags = [
        path
        for path in root.iterdir()
        if path.is_dir()
        and (
            (path / "events.jsonl").exists()
            or (path / "servo_steps.csv").exists()
            or (path / "analysis.html").exists()
        )
    ]
    return sorted(bags, key=lambda path: path.stat().st_mtime, reverse=True)


def open_existing_bag_analysis(directory: Path) -> Path:
    paths = BagPaths(
        directory=directory,
        events_jsonl=directory / "events.jsonl",
        servo_csv=directory / "servo_steps.csv",
        analysis_html=directory / "analysis.html",
    )
    if not paths.analysis_html.exists():
        rows = read_servo_rows_from_directory(directory)
        paths.analysis_html.write_text(build_analysis_html(rows, directory.name), encoding="utf-8")
    return paths.analysis_html


def read_servo_rows_from_directory(directory: Path) -> list[dict[str, str]]:
    servo_csv = directory / "servo_steps.csv"
    if not servo_csv.exists():
        raise FileNotFoundError(f"No servo_steps.csv in {directory}")
    with servo_csv.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_analysis_html(rows: list[dict[str, str]], title: str) -> str:
    labels = [f"{row['step']}. C{row['cell']} {row['name']}" for row in rows]
    series = {
        f"servo{index}": [float(row[f"servo{index}"]) for row in rows]
        for index in range(1, 6)
    }
    series["servo6_gripper"] = [float(row["servo6_gripper"]) for row in rows]
    speeds = [float(row["speed_percent"]) for row in rows]
    colors = ["#2563eb", "#0f766e", "#f97316", "#7c3aed", "#dc2626", "#111827"]
    chart = _build_svg_chart(labels, series, speeds, colors)
    rows_html = "\n".join(
        "<tr>"
        f"<td>{escape(row['step'])}</td>"
        f"<td>{escape(row['cell'])}</td>"
        f"<td>{escape(row['name'])}</td>"
        f"<td>{escape(row['speed_percent'])}%</td>"
        f"<td>{escape(row['servo1'])}</td>"
        f"<td>{escape(row['servo2'])}</td>"
        f"<td>{escape(row['servo3'])}</td>"
        f"<td>{escape(row['servo4'])}</td>"
        f"<td>{escape(row['servo5'])}</td>"
        f"<td>{escape(row['servo6_gripper'])}</td>"
        "</tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>v1.3 Bag Analysis - {escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f8fafc; color: #172033; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .muted {{ color: #64748b; margin-bottom: 22px; }}
    .panel {{ background: #fff; border: 1px solid #dbe4ee; padding: 18px; margin-bottom: 18px; }}
    .legend span {{ display: inline-block; margin-right: 14px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; font-size: 13px; }}
    th {{ background: #eef6f8; }}
    svg {{ width: 100%; height: auto; }}
  </style>
</head>
<body>
<main>
  <h1>v1.3 Bag Analysis</h1>
  <div class="muted">{escape(title)} / servo target angles and speed profile</div>
  <section class="panel">
    <div class="legend">
      <span style="color:#2563eb">servo1</span>
      <span style="color:#0f766e">servo2</span>
      <span style="color:#f97316">servo3</span>
      <span style="color:#7c3aed">servo4</span>
      <span style="color:#dc2626">servo5</span>
      <span style="color:#111827">servo6 gripper</span>
    </div>
    {chart}
  </section>
  <section class="panel">
    <h2>Cell Sequence</h2>
    <table>
      <thead>
        <tr><th>Step</th><th>Cell</th><th>Name</th><th>Speed</th><th>S1</th><th>S2</th><th>S3</th><th>S4</th><th>S5</th><th>Grip</th></tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </section>
</main>
</body>
</html>
"""


def _build_svg_chart(
    labels: list[str],
    series: dict[str, list[float]],
    speeds: list[float],
    colors: list[str],
) -> str:
    if not labels:
        return "<p>No servo data recorded yet.</p>"
    width = 1100
    height = 520
    left = 56
    right = 24
    top = 28
    bottom = 135
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_x = max(1, len(labels) - 1)

    def x_at(index: int) -> float:
        return left + (plot_w * index / max_x)

    def y_at(value: float) -> float:
        return top + plot_h - (plot_h * value / 180.0)

    grid = []
    for angle in range(0, 181, 30):
        y = y_at(angle)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#e2e8f0"/>'
            f'<text x="10" y="{y + 4:.1f}" font-size="12" fill="#64748b">{angle}</text>'
        )

    lines = []
    for color, (name, values) in zip(colors, series.items()):
        points = " ".join(f"{x_at(i):.1f},{y_at(value):.1f}" for i, value in enumerate(values))
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"><title>{name}</title></polyline>')
        for i, value in enumerate(values):
            lines.append(f'<circle cx="{x_at(i):.1f}" cy="{y_at(value):.1f}" r="3" fill="{color}"><title>{name}: {value}</title></circle>')

    speed_marks = []
    for i, speed in enumerate(speeds):
        if speed < 100:
            x = x_at(i)
            speed_marks.append(
                f'<rect x="{x - 10:.1f}" y="{top}" width="20" height="{plot_h}" fill="#fde68a" opacity="0.28">'
                f"<title>speed {speed}%</title></rect>"
            )

    ticks = []
    for i, label in enumerate(labels):
        x = x_at(i)
        short = escape(label[:28])
        ticks.append(f'<line x1="{x:.1f}" y1="{top + plot_h}" x2="{x:.1f}" y2="{top + plot_h + 6}" stroke="#94a3b8"/>')
        ticks.append(
            f'<text transform="translate({x - 4:.1f},{top + plot_h + 18:.1f}) rotate(58)" '
            f'font-size="11" fill="#475569">{short}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="servo graph">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>'
        + "".join(speed_marks)
        + "".join(grid)
        + f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#334155"/>'
        + f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#334155"/>'
        + "".join(lines)
        + "".join(ticks)
        + '<text x="10" y="18" font-size="12" fill="#64748b">angle(deg), yellow band = 50% speed</text>'
        + "</svg>"
    )
