from __future__ import annotations

from dataclasses import dataclass, field


EMPTY = ""
HUMAN = "O"
ROBOT = "X"

WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


@dataclass
class GameState:
    board: list[str] = field(default_factory=lambda: [EMPTY] * 9)

    def reset(self) -> None:
        self.board = [EMPTY] * 9

    def clone(self) -> "GameState":
        return GameState(self.board.copy())

    def available_moves(self) -> list[int]:
        return [index for index, mark in enumerate(self.board) if mark == EMPTY]

    def make_move(self, cell: int, mark: str) -> None:
        validate_cell(cell)
        if mark not in (HUMAN, ROBOT):
            raise ValueError(f"Invalid mark: {mark}")
        if self.board[cell] != EMPTY:
            raise ValueError(f"Cell {cell} is already occupied")
        self.board[cell] = mark

    def force_move(self, cell: int, mark: str) -> None:
        validate_cell(cell)
        if mark not in (EMPTY, HUMAN, ROBOT):
            raise ValueError(f"Invalid mark: {mark}")
        self.board[cell] = mark

    def winner(self) -> str:
        for a, b, c in WIN_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return EMPTY

    def winning_line(self) -> tuple[int, int, int] | None:
        for line in WIN_LINES:
            a, b, c = line
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return line
        return None

    def is_draw(self) -> bool:
        return self.winner() == EMPTY and EMPTY not in self.board

    def is_finished(self) -> bool:
        return self.winner() != EMPTY or self.is_draw()


def validate_cell(cell: int) -> None:
    if not 0 <= cell <= 8:
        raise ValueError(f"Cell must be 0-8, got {cell}")

