import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai import analyze_moves, choose_best_move
from game import HUMAN, ROBOT, GameState


class AiTest(unittest.TestCase):
    def test_ai_takes_immediate_win(self):
        state = GameState([ROBOT, ROBOT, "", HUMAN, HUMAN, "", "", "", ""])
        self.assertEqual(choose_best_move(state), 2)
        self.assertEqual(analyze_moves(state)[2].category, "win")

    def test_ai_blocks_immediate_loss(self):
        state = GameState([HUMAN, HUMAN, "", ROBOT, "", "", "", "", ROBOT])
        self.assertEqual(choose_best_move(state), 2)
        self.assertEqual(analyze_moves(state)[2].category, "block")

    def test_ai_never_loses_from_empty_board_after_human_center(self):
        state = GameState()
        state.make_move(4, HUMAN)
        move = choose_best_move(state)
        self.assertIn(move, {0, 2, 6, 8})
        self.assertGreaterEqual(analyze_moves(state)[move].score, 0)

    def test_robot_can_play_first_from_empty_board(self):
        state = GameState()
        self.assertEqual(choose_best_move(state), 4)
        self.assertEqual(analyze_moves(state)[4].category, "safe")

    def test_ai_never_loses_against_any_human_sequence(self):
        def play_all_human_lines(state):
            if state.is_finished():
                self.assertNotEqual(state.winner(), HUMAN)
                return

            for human_cell in state.available_moves():
                after_human = state.clone()
                after_human.make_move(human_cell, HUMAN)

                if after_human.is_finished():
                    self.assertNotEqual(after_human.winner(), HUMAN)
                    continue

                robot_cell = choose_best_move(after_human)
                self.assertIsNotNone(robot_cell)

                after_robot = after_human.clone()
                after_robot.make_move(robot_cell, ROBOT)
                play_all_human_lines(after_robot)

        play_all_human_lines(GameState())


if __name__ == "__main__":
    unittest.main()
