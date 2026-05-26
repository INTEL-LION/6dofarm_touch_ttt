import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from calibration import load_calibration
from robot_arm import MockRobotArm, format_servo_command


class RobotFlowTest(unittest.TestCase):
    def test_calibration_loads_all_nine_cells(self):
        calibration = load_calibration()
        self.assertEqual(set(calibration), set(range(9)))

    def test_mock_robot_reports_selected_cell_and_sequence(self):
        calibration = load_calibration()
        robot = MockRobotArm()
        result = robot.touch_cell(4, calibration, dry_run=True)
        self.assertIn("cell 4", result.message)
        self.assertIn("home -> approach -> touch -> approach -> home", result.message)

    def test_servo_command_clamps_gripper_to_closed_limit(self):
        command = format_servo_command([90, 91, 92, 93, 94, 120])
        self.assertEqual(command, "M 90,91,92,93,94,90")


if __name__ == "__main__":
    unittest.main()
