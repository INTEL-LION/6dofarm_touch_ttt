from __future__ import annotations

from dataclasses import dataclass

from game import EMPTY, HUMAN, ROBOT, GameState


PREFERRED_ORDER = (4, 0, 2, 6, 8, 1, 3, 5, 7)


@dataclass(frozen=True)
class MoveAnalysis:
    cell: int
    score: int
    category: str
    label: str
    is_best: bool = False


def analyze_moves(state: GameState) -> dict[int, MoveAnalysis]:
    moves = state.available_moves()
    if not moves or state.is_finished():
        return {}

    human_threats = _immediate_wins(state, HUMAN)
    raw: list[MoveAnalysis] = []

    for cell in moves:
        next_state = state.clone()
        next_state.make_move(cell, ROBOT)
        score = _minimax(next_state, HUMAN, depth=1)

        if next_state.winner() == ROBOT:
            category = "win"
            label = "즉시 승리"
        elif cell in human_threats:
            category = "block"
            label = "상대 승리 차단"
        elif score >= 0:
            category = "safe"
            label = "지지 않는 수"
        else:
            category = "risk"
            label = "위험한 수"

        raw.append(MoveAnalysis(cell=cell, score=score, category=category, label=label))

    best_cell = choose_best_move(state)
    return {
        item.cell: MoveAnalysis(
            cell=item.cell,
            score=item.score,
            category=item.category,
            label="추천: " + item.label if item.cell == best_cell else item.label,
            is_best=item.cell == best_cell,
        )
        for item in raw
    }


def choose_best_move(state: GameState) -> int | None:
    analyses = []
    for cell in state.available_moves():
        next_state = state.clone()
        next_state.make_move(cell, ROBOT)
        analyses.append((cell, _minimax(next_state, HUMAN, depth=1)))

    if not analyses:
        return None

    return max(analyses, key=lambda item: (item[1], -_order_rank(item[0])))[0]


def _minimax(state: GameState, turn: str, depth: int) -> int:
    winner = state.winner()
    if winner == ROBOT:
        return 10 - depth
    if winner == HUMAN:
        return depth - 10
    if state.is_draw():
        return 0

    if turn == ROBOT:
        best = -100
        for cell in state.available_moves():
            next_state = state.clone()
            next_state.make_move(cell, ROBOT)
            best = max(best, _minimax(next_state, HUMAN, depth + 1))
        return best

    best = 100
    for cell in state.available_moves():
        next_state = state.clone()
        next_state.make_move(cell, HUMAN)
        best = min(best, _minimax(next_state, ROBOT, depth + 1))
    return best


def _immediate_wins(state: GameState, mark: str) -> set[int]:
    wins: set[int] = set()
    for cell in state.available_moves():
        next_state = state.clone()
        next_state.make_move(cell, mark)
        if next_state.winner() == mark:
            wins.add(cell)
    return wins


def _order_rank(cell: int) -> int:
    return PREFERRED_ORDER.index(cell) if cell in PREFERRED_ORDER else len(PREFERRED_ORDER)

