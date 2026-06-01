import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from calibration import load_calibration
from robot_arm import (
    MockRobotArm,
    build_pick_and_place_sequence,
    build_sequence_step_trace,
    format_servo_command,
    format_speed_command,
    is_pre_place_slow_step,
    with_servo_angle,
)


class RobotFlowTest(unittest.TestCase):
    def test_calibration_loads_all_nine_cells(self):
        calibration = load_calibration()
        self.assertEqual(set(calibration.cells), set(range(9)))
        self.assertEqual(len(calibration.piece_source.approach_pose), 6)
        self.assertEqual(len(calibration.piece_source.pick_pose), 6)
        self.assertEqual(len(calibration.piece_source.lift_pose), 6)

    def test_mock_robot_reports_selected_cell_and_pick_place_sequence(self):
        calibration = load_calibration()
        robot = MockRobotArm()
        result = robot.touch_cell(4, calibration, dry_run=True)
        self.assertIn("cell 4", result.message)
        self.assertIn("pick -> lift -> cell approach -> place", result.message)

    def test_pick_and_place_sequence_opens_and_closes_gripper(self):
        sequence = build_pick_and_place_sequence(
            home_pose=[90, 90, 90, 90, 90, 90],
            piece_approach_pose=[1, 2, 3, 4, 5, 60],
            piece_pick_pose=[6, 7, 8, 9, 10, 60],
            piece_lift_pose=[],
            cell_hover_pose=[],
            cell_approach_pose=[11, 12, 13, 14, 15, 90],
            cell_place_pose=[16, 17, 18, 19, 20, 90],
            cell_exit_pose=[],
        )
        self.assertEqual(sequence[1], ("piece approach open", [1, 2, 3, 4, 5, 40.0]))
        self.assertEqual(sequence[3], ("piece pick close", [6, 7, 8, 9, 10, 90.0]))
        self.assertEqual(sequence[5], ("board transit holding", [1, 90.0, 3, 4, 5, 90.0]))
        self.assertEqual(sequence[6], ("cell hover holding", [11, 12, 13, 14, 15, 90.0]))
        self.assertEqual(sequence[9], ("cell release", [16, 17, 18, 19, 20, 40.0]))
        self.assertEqual(sequence[10], ("cell vertical lift open", [11, 12, 13, 14, 15, 40.0]))

    def test_release_lift_uses_exit_pose_without_hover_twist(self):
        sequence = build_pick_and_place_sequence(
            home_pose=[90, 90, 90, 90, 90, 90],
            piece_approach_pose=[60, 163, 130, 180, 63, 60],
            piece_pick_pose=[60, 159, 153, 170, 75, 90],
            piece_lift_pose=[75, 163, 125, 180, 63, 90],
            cell_hover_pose=[25, 110, 110, 90, 90, 90],
            cell_approach_pose=[5, 104, 107, 90, 90, 90],
            cell_place_pose=[5, 104, 107, 90, 90, 90],
            cell_exit_pose=[5, 110, 110, 90, 90, 90],
        )
        self.assertEqual(sequence[9], ("cell release", [5, 104, 107, 90, 90, 40.0]))
        self.assertEqual(sequence[10], ("cell vertical lift open", [5, 110, 110, 90, 90, 40.0]))
        self.assertNotIn(("cell lift open", [25, 110, 110, 90, 90, 40.0]), sequence)

    def test_release_path_uses_clear_pose_before_home(self):
        sequence = build_pick_and_place_sequence(
            home_pose=[90, 90, 90, 90, 90, 90],
            piece_approach_pose=[60, 163, 130, 180, 63, 60],
            piece_pick_pose=[60, 159, 153, 170, 75, 90],
            piece_lift_pose=[75, 163, 125, 180, 63, 90],
            cell_hover_pose=[25, 110, 110, 90, 90, 90],
            cell_approach_pose=[5, 104, 107, 90, 90, 90],
            cell_place_pose=[5, 104, 107, 90, 90, 90],
            cell_exit_pose=[5, 110, 110, 90, 90, 90],
            cell_clear_pose=[5, 140, 140, 90, 90, 90],
        )
        self.assertEqual(sequence[11], ("cell clear open", [5, 140, 140, 90, 90, 40.0]))
        self.assertEqual(sequence[12], ("home", [90, 90, 90, 90, 90, 90]))

    def test_board_transit_sets_servo2_to_90_before_cell_hover(self):
        transit = with_servo_angle([75, 163, 125, 180, 63, 90], 1, 90.0, 90.0)
        self.assertEqual(transit, [75, 90.0, 125, 180, 63, 90.0])

    def test_servo_command_clamps_gripper_to_closed_limit(self):
        command = format_servo_command([90, 91, 92, 93, 94, 120])
        self.assertEqual(command, "M 90,91,92,93,94,90")

    def test_speed_command_clamps_to_supported_range(self):
        self.assertEqual(format_speed_command(50), "V 50")
        self.assertEqual(format_speed_command(5), "V 10")
        self.assertEqual(format_speed_command(150), "V 100")

    def test_only_pre_place_steps_are_slowed(self):
        self.assertTrue(is_pre_place_slow_step("cell hover holding"))
        self.assertTrue(is_pre_place_slow_step("cell approach holding"))
        self.assertTrue(is_pre_place_slow_step("cell place holding"))
        self.assertFalse(is_pre_place_slow_step("piece lift"))
        self.assertFalse(is_pre_place_slow_step("cell release"))

    def test_sequence_step_trace_marks_pre_place_speed_only(self):
        sequence = [
            ("piece lift", [1, 2, 3, 4, 5, 90]),
            ("cell hover holding", [6, 7, 8, 9, 10, 90]),
            ("cell approach holding", [11, 12, 13, 14, 15, 90]),
            ("cell place holding", [16, 17, 18, 19, 20, 90]),
            ("cell release", [16, 17, 18, 19, 20, 40]),
        ]
        trace = build_sequence_step_trace(sequence, dry_run=True)
        self.assertEqual([step["speed_percent"] for step in trace], [100, 50, 50, 50, 100])


if __name__ == "__main__":
    unittest.main()
