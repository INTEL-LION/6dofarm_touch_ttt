from __future__ import annotations

import json
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from calibration import CALIBRATION_PATH, load_calibration  # noqa: E402
from robot_arm import (  # noqa: E402
    ROBOT_CONFIG_PATH,
    build_pick_and_place_sequence,
    format_servo_command,
)


SERVO_NAMES = ("1 Base", "2 Shoulder", "3 Elbow", "4 Wrist Rotate", "5 Wrist Tilt", "6 Gripper")
STEP_CHOICES = {
    6: "06 board transit",
    9: "09 release",
    10: "10 release",
    11: "11 vertical lift",
    12: "12 clear",
}


class ArduinoConnection:
    def __init__(self, port: str, baud_rate: int, timeout_seconds: float) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.timeout_seconds = timeout_seconds
        self.connection = None

    def connect(self) -> None:
        if self.connection is not None and getattr(self.connection, "is_open", False):
            return

        serial_module = self._load_serial_module()
        self.connection = serial_module.Serial()
        self.connection.port = self.port
        self.connection.baudrate = self.baud_rate
        self.connection.timeout = self.timeout_seconds
        try:
            self.connection.dtr = False
            self.connection.rts = False
        except Exception:
            pass
        self.connection.open()
        time.sleep(2.5)
        if hasattr(self.connection, "reset_input_buffer"):
            self.connection.reset_input_buffer()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def command(self, line: str, expected_prefix: str = "OK") -> str:
        if self.connection is None:
            raise RuntimeError("Arduino is not connected")
        self.connection.write((line + "\n").encode("ascii"))
        deadline = time.time() + 10.0
        while time.time() < deadline:
            response = self.connection.readline().decode("ascii", errors="replace").strip()
            if not response or response == "OK READY":
                continue
            if response.startswith(expected_prefix):
                return response
            if response.startswith("ERR"):
                raise RuntimeError(response)
        raise RuntimeError(f"No matching response after command: {line}")

    def move(self, angles: list[float]) -> str:
        return self.command(format_servo_command(angles), "OK MOVE")

    def jog(self, servo_number: int, delta: int) -> list[int]:
        response = self.command(f"J {servo_number},{delta}", "OK ANGLES")
        payload = response.replace("OK ANGLES ", "", 1)
        return [int(item) for item in payload.split(",")]

    def query_angles(self) -> list[int]:
        response = self.command("Q", "OK ANGLES")
        payload = response.replace("OK ANGLES ", "", 1)
        return [int(item) for item in payload.split(",")]

    def _load_serial_module(self):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required. Install it with: python -m pip install pyserial") from exc
        return serial


class AdjustSequencePoseApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Adjust Sequence Pose")
        self.config = json.loads(ROBOT_CONFIG_PATH.read_text(encoding="utf-8"))
        self.calibration_data = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        self.arduino = ArduinoConnection(
            port=self.config.get("port", "COM3"),
            baud_rate=int(self.config.get("baud_rate", 9600)),
            timeout_seconds=float(self.config.get("timeout_seconds", 2)),
        )
        self.current_angles = [90, 90, 90, 90, 90, 90]
        self.cell_var = tk.IntVar(value=0)
        self.step_var = tk.IntVar(value=10)
        self.angles_var = tk.StringVar(value="Not connected")
        self.status_var = tk.StringVar(value="Connect first. Then go to a sequence step and jog motors.")
        self._build_ui()

    def _build_ui(self) -> None:
        self.root.geometry("820x620")
        self.root.minsize(780, 560)

        main = tk.Frame(self.root, padx=16, pady=16)
        main.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(main)
        top.pack(fill=tk.X)
        tk.Button(top, text="Connect", command=self._connect).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(top, text="Cell").pack(side=tk.LEFT)
        tk.Spinbox(top, from_=0, to=8, width=4, textvariable=self.cell_var).pack(side=tk.LEFT, padx=(4, 12))
        tk.Label(top, text="Stop Step").pack(side=tk.LEFT)
        tk.OptionMenu(top, self.step_var, *STEP_CHOICES.keys()).pack(side=tk.LEFT, padx=(4, 12))
        tk.Button(top, text="Go to Selected Step", command=self._go_to_step).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(top, text="Query Angles", command=self._query).pack(side=tk.LEFT)

        tk.Label(main, textvariable=self.angles_var, font=("Consolas", 14, "bold")).pack(anchor="w", pady=(16, 6))
        tk.Label(main, textvariable=self.status_var).pack(anchor="w")

        jog_frame = tk.LabelFrame(main, text="Jog Actual Motors at Current Step")
        jog_frame.pack(fill=tk.X, pady=(16, 8))

        for index, name in enumerate(SERVO_NAMES, start=1):
            row = tk.Frame(jog_frame)
            row.pack(fill=tk.X, padx=8, pady=4)
            tk.Label(row, text=name, width=18, anchor="w").pack(side=tk.LEFT)
            for delta in (-10, -5, -1, 1, 5, 10):
                tk.Button(row, text=f"{delta:+}", width=5, command=lambda s=index, d=delta: self._jog(s, d)).pack(
                    side=tk.LEFT,
                    padx=2,
                )

        save_frame = tk.LabelFrame(main, text="Save Adjusted Current Angles")
        save_frame.pack(fill=tk.X, pady=(12, 8))
        tk.Button(save_frame, text="Save as Exit Pose", command=lambda: self._save_pose("exit_pose")).pack(
            side=tk.LEFT,
            padx=8,
            pady=8,
        )
        tk.Button(save_frame, text="Save as Clear Pose", command=lambda: self._save_pose("clear_pose")).pack(
            side=tk.LEFT,
            padx=4,
            pady=8,
        )
        tk.Button(save_frame, text="Save as Hover Pose", command=lambda: self._save_pose("hover_pose")).pack(
            side=tk.LEFT,
            padx=4,
            pady=8,
        )

        note = tk.Text(main, height=10, wrap=tk.WORD)
        note.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        note.insert(
            tk.END,
            "Recommended ring-avoidance flow:\n"
            "1. Choose cell 0, 1, or 2.\n"
            "2. Choose step 6 to inspect the new board-transit waypoint.\n"
            "3. Choose step 11 to adjust the vertical lift after release.\n"
            "4. Jog only the joints needed. Keep Base nearly unchanged near the ring if possible.\n"
            "5. Save as Exit Pose for immediate lift, or Clear Pose before returning home.\n"
            "6. Test with run_debug_cell_sequence_real.bat before using the game UI.\n",
        )
        note.configure(state=tk.DISABLED)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _connect(self) -> None:
        try:
            self.arduino.connect()
            response = self.arduino.command("PING", "OK PONG")
            self.current_angles = self.arduino.query_angles()
            self._update_angles()
            self.status_var.set(f"Connected: {response}")
        except Exception as exc:
            messagebox.showerror("Connection error", str(exc))

    def _go_to_step(self) -> None:
        try:
            sequence = self._build_sequence()
            stop_step = int(self.step_var.get())
            for index, (name, angles) in enumerate(sequence, start=1):
                self.arduino.move(angles)
                self.current_angles = [int(round(item)) for item in angles]
                self.status_var.set(f"Sent step {index}: {name}")
                self._update_angles()
                self.root.update_idletasks()
                time.sleep(float(self.config.get("move_delay_seconds", 1.1)))
                if index == stop_step:
                    break
            self.current_angles = self.arduino.query_angles()
            self._update_angles()
            self.status_var.set(f"Stopped at step {stop_step}. Jog motors and save the adjusted pose.")
        except Exception as exc:
            messagebox.showerror("Sequence error", str(exc))

    def _build_sequence(self):
        calibration = load_calibration()
        pose = calibration.cells[int(self.cell_var.get())]
        return build_pick_and_place_sequence(
            home_pose=[90, 90, 90, 90, 90, 90],
            piece_approach_pose=calibration.piece_source.approach_pose,
            piece_pick_pose=calibration.piece_source.pick_pose,
            piece_lift_pose=calibration.piece_source.lift_pose,
            cell_hover_pose=pose.hover_pose,
            cell_approach_pose=pose.approach_pose,
            cell_place_pose=pose.approach_pose,
            cell_exit_pose=pose.exit_pose,
            cell_clear_pose=pose.clear_pose,
        )

    def _query(self) -> None:
        try:
            self.current_angles = self.arduino.query_angles()
            self._update_angles()
            self.status_var.set("Angles updated.")
        except Exception as exc:
            messagebox.showerror("Query error", str(exc))

    def _jog(self, servo_number: int, delta: int) -> None:
        try:
            self.current_angles = self.arduino.jog(servo_number, delta)
            self._update_angles()
            self.status_var.set(f"Jogged servo {servo_number} by {delta:+}.")
        except Exception as exc:
            messagebox.showerror("Jog error", str(exc))

    def _save_pose(self, pose_name: str) -> None:
        cell = int(self.cell_var.get())
        cell_data = self.calibration_data.setdefault("cells", {}).setdefault(str(cell), {})
        cell_data[pose_name] = self.current_angles.copy()
        CALIBRATION_PATH.write_text(json.dumps(self.calibration_data, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved cell {cell} {pose_name}: {self.current_angles}")

    def _update_angles(self) -> None:
        self.angles_var.set("Current angles: " + ", ".join(str(angle) for angle in self.current_angles))

    def _on_close(self) -> None:
        self.arduino.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    AdjustSequencePoseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
