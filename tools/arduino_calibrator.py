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

from calibration import CALIBRATION_PATH  # noqa: E402
from robot_arm import ROBOT_CONFIG_PATH  # noqa: E402


SERVO_NAMES = ("1 Base", "2 Shoulder", "3 Elbow", "4 Wrist Rotate", "5 Wrist Tilt", "6 Gripper")


class ArduinoConnection:
    def __init__(self, port: str, baud_rate: int, timeout_seconds: float) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.timeout_seconds = timeout_seconds
        self.connection = None

    def connect(self) -> None:
        serial_module = self._load_serial_module()
        self.connection = serial_module.Serial(self.port, self.baud_rate, timeout=self.timeout_seconds)
        time.sleep(2.0)
        if hasattr(self.connection, "reset_input_buffer"):
            self.connection.reset_input_buffer()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def command(self, line: str) -> str:
        if self.connection is None:
            raise RuntimeError("Arduino is not connected")
        self.connection.write((line + "\n").encode("ascii"))
        response = self.connection.readline().decode("ascii", errors="replace").strip()
        if not response:
            raise RuntimeError(f"No response after command: {line}")
        return response

    def query_angles(self) -> list[int]:
        response = self.command("Q")
        if not response.startswith("OK ANGLES "):
            raise RuntimeError(f"Unexpected angle response: {response}")
        payload = response.replace("OK ANGLES ", "", 1)
        return [int(item) for item in payload.split(",")]

    def jog(self, servo_number: int, delta: int) -> list[int]:
        response = self.command(f"J {servo_number},{delta}")
        if not response.startswith("OK ANGLES "):
            raise RuntimeError(f"Unexpected jog response: {response}")
        payload = response.replace("OK ANGLES ", "", 1)
        return [int(item) for item in payload.split(",")]

    def home(self) -> list[int]:
        response = self.command("H")
        if not response.startswith("OK"):
            raise RuntimeError(f"Unexpected home response: {response}")
        return self.query_angles()

    def _load_serial_module(self):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required. Install it with: python -m pip install pyserial") from exc
        return serial


class CalibratorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Arduino Robot Arm Calibrator")
        self.config = json.loads(ROBOT_CONFIG_PATH.read_text(encoding="utf-8"))
        self.calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        self.arduino = ArduinoConnection(
            port=self.config.get("port", "COM3"),
            baud_rate=int(self.config.get("baud_rate", 115200)),
            timeout_seconds=float(self.config.get("timeout_seconds", 2)),
        )
        self.current_angles: list[int] = [90, 90, 90, 90, 90, 90]
        self.cell_var = tk.IntVar(value=0)
        self.angles_var = tk.StringVar(value="Not connected")
        self.status_var = tk.StringVar(value="Connect first. Arduino Serial Monitor should be closed.")
        self._build_ui()

    def _build_ui(self) -> None:
        self.root.geometry("760x560")
        self.root.minsize(700, 520)

        main = tk.Frame(self.root, padx=16, pady=16)
        main.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(main)
        top.pack(fill=tk.X)

        tk.Button(top, text="Connect", command=self._connect).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(top, text="Query Angles", command=self._query).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(top, text="Home", command=self._home).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(top, text=f"Port: {self.config.get('port', 'COM3')}").pack(side=tk.RIGHT)

        tk.Label(main, textvariable=self.angles_var, font=("Consolas", 14, "bold")).pack(anchor="w", pady=(16, 8))
        tk.Label(main, textvariable=self.status_var).pack(anchor="w")

        jog_frame = tk.LabelFrame(main, text="Jog Servos")
        jog_frame.pack(fill=tk.X, pady=(16, 8))

        for index, name in enumerate(SERVO_NAMES, start=1):
            row = tk.Frame(jog_frame)
            row.pack(fill=tk.X, padx=8, pady=4)
            tk.Label(row, text=name, width=16, anchor="w").pack(side=tk.LEFT)
            for delta in (-10, -5, -1, 1, 5, 10):
                tk.Button(row, text=f"{delta:+}", width=5, command=lambda s=index, d=delta: self._jog(s, d)).pack(
                    side=tk.LEFT,
                    padx=2,
                )

        save_frame = tk.LabelFrame(main, text="Save Current Angles to Calibration")
        save_frame.pack(fill=tk.X, pady=(12, 8))

        tk.Label(save_frame, text="Cell 0-8").pack(side=tk.LEFT, padx=(8, 4), pady=8)
        tk.Spinbox(save_frame, from_=0, to=8, width=4, textvariable=self.cell_var).pack(side=tk.LEFT, padx=(0, 12))
        tk.Button(save_frame, text="Save Approach Pose", command=lambda: self._save_pose("approach_pose")).pack(
            side=tk.LEFT,
            padx=4,
        )
        tk.Button(save_frame, text="Save Hover Pose", command=lambda: self._save_pose("hover_pose")).pack(
            side=tk.LEFT,
            padx=4,
        )
        tk.Button(save_frame, text="Save Exit Pose", command=lambda: self._save_pose("exit_pose")).pack(
            side=tk.LEFT,
            padx=4,
        )
        tk.Button(save_frame, text="Save Clear Pose", command=lambda: self._save_pose("clear_pose")).pack(
            side=tk.LEFT,
            padx=4,
        )
        tk.Button(save_frame, text="Save Touch Pose", command=lambda: self._save_pose("touch_pose")).pack(
            side=tk.LEFT,
            padx=4,
        )

        source_frame = tk.LabelFrame(main, text="Save Piece Storage Position")
        source_frame.pack(fill=tk.X, pady=(4, 8))
        tk.Button(
            source_frame,
            text="Save Piece Approach Pose",
            command=lambda: self._save_piece_source_pose("approach_pose"),
        ).pack(side=tk.LEFT, padx=8, pady=8)
        tk.Button(
            source_frame,
            text="Save Piece Pick Pose",
            command=lambda: self._save_piece_source_pose("pick_pose"),
        ).pack(side=tk.LEFT, padx=4, pady=8)
        tk.Button(
            source_frame,
            text="Save Piece Lift Pose",
            command=lambda: self._save_piece_source_pose("lift_pose"),
        ).pack(side=tk.LEFT, padx=4, pady=8)

        note = tk.Text(main, height=8, wrap=tk.WORD)
        note.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        note.insert(
            tk.END,
            "Calibration flow:\n"
            "1. Close Arduino Serial Monitor.\n"
            "2. Click Connect.\n"
            "3. Use Jog buttons to move one servo at a time.\n"
            "4. Save a high hover pose for the selected cell.\n"
            "5. Save the approach pose where the piece should be released.\n"
            "6. For cells that hit the ring, save exit and clear poses with the same base angle.\n"
            "7. Move lightly to the board cell center and save the touch pose only if needed.\n"
            "8. Move to the piece storage area and save piece approach/pick/lift poses.\n"
            "9. Servo 6 is the gripper and is limited by Arduino to 0..90 degrees.\n",
        )
        note.configure(state=tk.DISABLED)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _connect(self) -> None:
        try:
            self.arduino.connect()
            response = self.arduino.command("PING")
            self.current_angles = self.arduino.query_angles()
            self._update_angles()
            self.status_var.set(f"Connected: {response}")
        except Exception as exc:
            messagebox.showerror("Connection error", str(exc))

    def _query(self) -> None:
        try:
            self.current_angles = self.arduino.query_angles()
            self._update_angles()
            self.status_var.set("Angles updated.")
        except Exception as exc:
            messagebox.showerror("Query error", str(exc))

    def _home(self) -> None:
        try:
            self.current_angles = self.arduino.home()
            self._update_angles()
            self.status_var.set("Moved to home.")
        except Exception as exc:
            messagebox.showerror("Home error", str(exc))

    def _jog(self, servo_number: int, delta: int) -> None:
        try:
            self.current_angles = self.arduino.jog(servo_number, delta)
            self._update_angles()
            self.status_var.set(f"Jogged servo {servo_number} by {delta:+}.")
        except Exception as exc:
            messagebox.showerror("Jog error", str(exc))

    def _save_pose(self, pose_name: str) -> None:
        cell = int(self.cell_var.get())
        cell_data = self.calibration.setdefault("cells", {}).setdefault(str(cell), {})
        cell_data[pose_name] = self.current_angles.copy()
        CALIBRATION_PATH.write_text(json.dumps(self.calibration, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved cell {cell} {pose_name}: {self.current_angles}")

    def _save_piece_source_pose(self, pose_name: str) -> None:
        source_data = self.calibration.setdefault("piece_source", {})
        source_data[pose_name] = self.current_angles.copy()
        CALIBRATION_PATH.write_text(json.dumps(self.calibration, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved piece_source {pose_name}: {self.current_angles}")

    def _update_angles(self) -> None:
        self.angles_var.set("Current angles: " + ", ".join(str(angle) for angle in self.current_angles))

    def _on_close(self) -> None:
        self.arduino.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    CalibratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
