from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from robot_arm import ROBOT_CONFIG_PATH  # noqa: E402


def main() -> int:
    config = json.loads(ROBOT_CONFIG_PATH.read_text(encoding="utf-8"))
    port = config.get("port", "COM3")
    baud_rate = int(config.get("baud_rate", 115200))
    timeout_seconds = float(config.get("timeout_seconds", 2))

    serial_module = load_serial_module()

    print(f"Connecting to Arduino on {port} at {baud_rate} baud...")
    try:
        with serial_module.Serial(port, baud_rate, timeout=timeout_seconds) as connection:
            time.sleep(2.0)
            if hasattr(connection, "reset_input_buffer"):
                connection.reset_input_buffer()

            for command, expected in (("PING", "OK PONG"), ("Q", "OK ANGLES"), ("H", "OK HOME"), ("Q", "OK ANGLES")):
                response = send_line(connection, command, expected)
                print(f"> {command}")
                print(f"< {response}")
    except Exception as exc:
        print("")
        print("Arduino connection failed.")
        print(f"Reason: {exc}")
        print("")
        print("Check these first:")
        print("1. Close Arduino Serial Monitor and Serial Plotter.")
        print("2. Close any other program using the same COM port.")
        print("3. Unplug and reconnect the Arduino USB cable.")
        print("4. Confirm config/robot.json has the correct COM port.")
        return 1

    print("Arduino connection check finished.")
    return 0


def load_serial_module():
    try:
        import serial
    except ImportError:
        print("pyserial is required. Install it with: python -m pip install pyserial")
        raise
    return serial


def send_line(connection, command: str, expected_prefix: str) -> str:
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

    raise RuntimeError(f"No matching response after command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
