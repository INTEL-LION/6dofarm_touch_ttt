from __future__ import annotations

import json
import time


def main() -> int:
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
    except ImportError:
        print("ROS2 Python packages are not installed in this environment.")
        print("Install/source ROS2, then run this file again.")
        print("This bridge is optional; v1.1 robot control does not require ROS2.")
        return 1

    class RobotTttBridge(Node):
        def __init__(self) -> None:
            super().__init__("robot_ttt_v1_1_bridge")
            self.event_pub = self.create_publisher(String, "/robot_arm/event", 10)
            self.angle_pub = self.create_publisher(String, "/robot_arm/servo_angles", 10)
            self.timer = self.create_timer(1.0, self.publish_heartbeat)

        def publish_heartbeat(self) -> None:
            event = String()
            event.data = json.dumps(
                {
                    "version": "v1.1",
                    "event": "heartbeat",
                    "time": time.time(),
                    "note": "bridge skeleton; integrate UI events next",
                }
            )
            self.event_pub.publish(event)

    rclpy.init()
    node = RobotTttBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

