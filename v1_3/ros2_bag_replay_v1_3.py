from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BAG_ROOT = ROOT / "bags"


def latest_events_file() -> Path:
    candidates = sorted(BAG_ROOT.glob("v1_3_bag_*/events.jsonl"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No v1.3 events.jsonl found under {BAG_ROOT}")
    return candidates[-1]


def iter_events(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a v1.3 UI bag JSONL file into ROS2 topics.")
    parser.add_argument("--events", type=Path, default=None, help="Path to bags/.../events.jsonl. Defaults to latest.")
    parser.add_argument("--rate", type=float, default=1.0, help="Replay speed multiplier.")
    parser.add_argument("--once", action="store_true", help="Publish all events once and exit.")
    args = parser.parse_args()

    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import Float64MultiArray, String
    except ImportError:
        print("ROS2 Python packages are not installed or sourced.")
        print("In WSL, run: source /opt/ros/<distro>/setup.bash")
        return 1

    events_path = args.events or latest_events_file()
    events = list(iter_events(events_path))
    if not events:
        print(f"No events in {events_path}")
        return 1

    class V13BagReplay(Node):
        def __init__(self) -> None:
            super().__init__("robot_ttt_v1_3_bag_replay")
            self.string_publishers: dict[str, object] = {}
            self.angle_pub = self.create_publisher(Float64MultiArray, "/robot_arm/target_servo_angles_array", 10)

        def publish_event(self, event: dict) -> None:
            topic = str(event["topic"])
            payload = event["data"]
            publisher = self.string_publishers.get(topic)
            if publisher is None:
                publisher = self.create_publisher(String, topic, 10)
                self.string_publishers[topic] = publisher

            message = String()
            message.data = json.dumps(payload, ensure_ascii=False)
            publisher.publish(message)

            if topic == "/robot_arm/target_servo_angles":
                angles = payload.get("angles", [])
                array_message = Float64MultiArray()
                array_message.data = [float(value) for value in angles]
                self.angle_pub.publish(array_message)

    rclpy.init()
    node = V13BagReplay()
    print(f"Replaying {events_path}")
    print("Published topics include /robot_arm/target_servo_angles_array for plotting.")

    try:
        while rclpy.ok():
            previous_time = None
            for event in events:
                if previous_time is not None:
                    delay = max(0.0, (float(event["time"]) - previous_time) / max(args.rate, 0.01))
                    time.sleep(delay)
                previous_time = float(event["time"])
                node.publish_event(event)
                rclpy.spin_once(node, timeout_sec=0.0)
            if args.once:
                break
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
