import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from game import HUMAN, ROBOT, GameState


class GameStateTest(unittest.TestCase):
    def test_winner_rows_columns_and_diagonals(self):
        state = GameState()
        state.force_move(0, ROBOT)
        state.force_move(1, ROBOT)
        state.force_move(2, ROBOT)
        self.assertEqual(state.winner(), ROBOT)
        self.assertEqual(state.winning_line(), (0, 1, 2))

    def test_draw_detection(self):
        state = GameState([ROBOT, HUMAN, ROBOT, ROBOT, HUMAN, HUMAN, HUMAN, ROBOT, ROBOT])
        self.assertTrue(state.is_draw())

    def test_occupied_cell_is_rejected(self):
        state = GameState()
        state.make_move(4, HUMAN)
        with self.assertRaises(ValueError):
            state.make_move(4, ROBOT)


if __name__ == "__main__":
    unittest.main()

