from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from ai import MoveAnalysis, analyze_moves, choose_best_move
from calibration import load_calibration
from game import HUMAN, ROBOT, GameState
from robot_arm import create_robot_arm, load_robot_config


PALETTE = {
    "bg": "#eef6f8",
    "surface": "#ffffff",
    "surface_alt": "#e8f1ff",
    "ink": "#172033",
    "muted": "#64748b",
    "line": "#cad7e3",
    "primary": "#2563eb",
    "primary_dark": "#1d4ed8",
    "teal": "#0f766e",
    "coral": "#f97316",
    "danger": "#dc2626",
    "win": "#86efac",
    "block": "#fde68a",
    "safe": "#bfdbfe",
    "risk": "#fecaca",
    "selected": "#5eead4",
    "occupied": "#dbe4ee",
    "board": "#d7e5ef",
}

CELL_COLORS = {
    "win": PALETTE["win"],
    "block": PALETTE["block"],
    "safe": PALETTE["safe"],
    "risk": PALETTE["risk"],
}


class TicTacToeRobotApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("6축 로봇팔 틱택토")
        self.state = GameState()
        self.calibration = load_calibration()
        self.robot_config = load_robot_config()
        self.robot = create_robot_arm(self.robot_config)
        self.robot_dry_run = bool(self.robot_config.get("dry_run", True))
        self.robot_connected = self.robot_dry_run
        self.analyses: dict[int, MoveAnalysis] = {}
        self.selected_robot_cell: int | None = None
        self.waiting_for_human = True

        self.status_var = tk.StringVar()
        self.selected_var = tk.StringVar(value="선택된 로봇 칸: 없음")
        self.mode_var = tk.StringVar(value=self._mode_text())

        self.board_buttons: list[tk.Button] = []
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh()

    def _build_ui(self) -> None:
        self.root.geometry("1120x720")
        self.root.minsize(980, 660)
        self.root.configure(bg=PALETTE["bg"])

        main = tk.Frame(self.root, bg=PALETTE["bg"], padx=22, pady=22)
        main.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(main, bg=PALETTE["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(main, bg=PALETTE["surface"], padx=18, pady=18, highlightthickness=1)
        right.configure(highlightbackground=PALETTE["line"], highlightcolor=PALETTE["line"])
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(22, 0))

        tk.Label(
            left,
            text="6축 로봇팔 틱택토",
            bg=PALETTE["bg"],
            fg=PALETTE["ink"],
            font=("맑은 고딕", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            left,
            text="사람은 O, 로봇은 X입니다. 로봇 선공도 가능합니다.",
            bg=PALETTE["bg"],
            fg=PALETTE["muted"],
            font=("맑은 고딕", 11),
        ).pack(anchor="w", pady=(2, 14))

        board_frame = tk.Frame(left, bg=PALETTE["board"], padx=8, pady=8)
        board_frame.pack(anchor="w")

        for cell in range(9):
            button = tk.Button(
                board_frame,
                text=str(cell),
                width=6,
                height=3,
                font=("맑은 고딕", 30, "bold"),
                bg=PALETTE["surface"],
                fg=PALETTE["ink"],
                activebackground=PALETTE["surface_alt"],
                activeforeground=PALETTE["ink"],
                relief=tk.FLAT,
                bd=0,
                command=lambda c=cell: self._on_cell_click(c),
            )
            button.grid(row=cell // 3, column=cell % 3, padx=5, pady=5, sticky="nsew")
            self.board_buttons.append(button)

        info = tk.Frame(left, bg=PALETTE["bg"], pady=12)
        info.pack(fill=tk.X, anchor="w")
        tk.Label(info, textvariable=self.status_var, bg=PALETTE["bg"], fg=PALETTE["ink"], font=("맑은 고딕", 13, "bold")).pack(anchor="w")
        tk.Label(info, textvariable=self.selected_var, bg=PALETTE["bg"], fg=PALETTE["teal"], font=("맑은 고딕", 12)).pack(anchor="w", pady=(5, 0))
        tk.Label(info, textvariable=self.mode_var, bg=PALETTE["bg"], fg=PALETTE["muted"], font=("맑은 고딕", 10)).pack(anchor="w", pady=(5, 0))

        legend = tk.Frame(left, bg=PALETTE["bg"])
        legend.pack(anchor="w", pady=(4, 0))
        for label, color in (
            ("승리", CELL_COLORS["win"]),
            ("차단", CELL_COLORS["block"]),
            ("안전", CELL_COLORS["safe"]),
            ("위험", CELL_COLORS["risk"]),
        ):
            tk.Label(legend, text=f"  {label}  ", bg=color, fg=PALETTE["ink"], font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(right, text="실행 순서", bg=PALETTE["surface"], fg=PALETTE["ink"], font=("맑은 고딕", 18, "bold")).pack(anchor="w")
        tk.Label(
            right,
            text="로봇 선공이면 빈 보드에서 예측을 누르세요.",
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
            font=("맑은 고딕", 10),
        ).pack(anchor="w", pady=(0, 10))

        actions = tk.Frame(right, bg=PALETTE["surface"])
        actions.pack(fill=tk.X)

        self._action_button(actions, "1. 로봇 연결", self._connect_robot, PALETTE["primary"]).pack(fill=tk.X, pady=4)
        self._action_button(actions, "2. 다음 수 예측", self._predict_robot_move, PALETTE["teal"]).pack(fill=tk.X, pady=4)
        self._action_button(actions, "3. 추천 칸 선택", self._select_recommended_robot_move, PALETTE["coral"]).pack(fill=tk.X, pady=4)
        self._action_button(actions, "4. 선택 칸에 말 놓기", self._execute_robot_touch, PALETTE["primary_dark"]).pack(fill=tk.X, pady=4)

        utility = tk.Frame(right, bg=PALETTE["surface"], pady=8)
        utility.pack(fill=tk.X)
        self._secondary_button(utility, "로봇 선공 준비", self._prepare_robot_first).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "전체 픽앤플레이스 경로 확인", self._show_all_calibration).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "새 게임", self._new_game).pack(fill=tk.X, pady=3)

        tk.Label(right, text="로봇 로그", bg=PALETTE["surface"], fg=PALETTE["ink"], font=("맑은 고딕", 14, "bold")).pack(anchor="w", pady=(14, 5))
        self.log_text = tk.Text(
            right,
            width=42,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#dbeafe",
            insertbackground="#dbeafe",
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _action_button(self, parent: tk.Widget, text: str, command, color: str) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="#ffffff",
            activebackground=color,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=10,
            font=("맑은 고딕", 12, "bold"),
        )

    def _secondary_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=PALETTE["surface_alt"],
            fg=PALETTE["ink"],
            activebackground="#dbeafe",
            activeforeground=PALETTE["ink"],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=8,
            font=("맑은 고딕", 10, "bold"),
        )

    def _on_cell_click(self, cell: int) -> None:
        if self.state.is_finished():
            return

        if self.waiting_for_human:
            try:
                self.state.make_move(cell, HUMAN)
            except ValueError as exc:
                messagebox.showwarning("입력 오류", str(exc))
                return
            self.waiting_for_human = False
            self.selected_robot_cell = None
            self.analyses = {}
            self._refresh()
            return

        if cell in self.analyses:
            self.selected_robot_cell = cell
            self.selected_var.set(f"선택된 로봇 칸: {cell} ({self.analyses[cell].label})")
            self._refresh()

    def _prepare_robot_first(self) -> None:
        if any(self.state.board):
            messagebox.showinfo("로봇 선공", "새 게임 상태에서만 로봇 선공을 준비할 수 있습니다.")
            return
        self.waiting_for_human = False
        self.analyses = {}
        self.selected_robot_cell = None
        self.status_var.set("상태: 로봇 선공 준비 완료. 2번 예측을 누르세요.")
        self._append_log("Robot-first mode prepared.")
        self._refresh()

    def _predict_robot_move(self) -> None:
        if self.state.is_finished():
            return
        if self.waiting_for_human and any(self.state.board):
            messagebox.showinfo("사람 차례", "먼저 사람의 수를 입력한 뒤 예측하세요.")
            return
        if not any(self.state.board):
            self.waiting_for_human = False
        self.analyses = analyze_moves(self.state)
        self.selected_robot_cell = None
        self.selected_var.set("선택된 로봇 칸: 없음")
        self._append_log("Predicted robot candidate moves.")
        self._refresh()

    def _select_recommended_robot_move(self) -> None:
        if self.waiting_for_human and any(self.state.board):
            messagebox.showinfo("사람 차례", "먼저 사람의 수를 입력하세요.")
            return
        if not self.analyses:
            self._predict_robot_move()
        best = choose_best_move(self.state)
        if best is None:
            return
        self.selected_robot_cell = best
        label = self.analyses[best].label if best in self.analyses else "추천"
        self.selected_var.set(f"선택된 로봇 칸: {best} ({label})")
        self._refresh()

    def _execute_robot_touch(self) -> None:
        if self.selected_robot_cell is None:
            messagebox.showinfo("선택 필요", "3번 추천 칸 선택을 먼저 누르세요.")
            return
        if not self.robot_dry_run and not self.robot_connected:
            messagebox.showerror("로봇 미연결", "로봇팔을 받친 상태에서 1번 로봇 연결을 먼저 누르세요.")
            return

        try:
            result = self.robot.touch_cell(self.selected_robot_cell, self.calibration, dry_run=self.robot_dry_run)
        except Exception as exc:
            messagebox.showerror("로봇 연결 오류", str(exc))
            return
        self._append_log(result.message)

        try:
            self.state.make_move(self.selected_robot_cell, ROBOT)
        except ValueError as exc:
            messagebox.showwarning("로봇 수 오류", str(exc))
            return

        self.selected_robot_cell = None
        self.analyses = {}
        self.waiting_for_human = not self.state.is_finished()
        self.selected_var.set("선택된 로봇 칸: 없음")
        self._refresh()

    def _new_game(self) -> None:
        self.state.reset()
        self.analyses = {}
        self.selected_robot_cell = None
        self.waiting_for_human = True
        self.selected_var.set("선택된 로봇 칸: 없음")
        self._append_log("New game started.")
        self._refresh()

    def _connect_robot(self) -> None:
        if self.robot_dry_run:
            self.robot_connected = True
            self._append_log("Dry-run mode: robot connection is not required.")
            self._refresh()
            return
        try:
            if hasattr(self.robot, "connect"):
                self.robot.connect()
            self.robot_connected = True
            self._append_log("Robot connected. Serial port is being kept open.")
        except Exception as exc:
            self.robot_connected = False
            messagebox.showerror("Robot connection error", str(exc))
        self._refresh()

    def _show_all_calibration(self) -> None:
        for cell in range(9):
            result = self.robot.touch_cell(cell, self.calibration, dry_run=True)
            self._append_log(result.message)

    def _refresh(self) -> None:
        winning_line = self.state.winning_line() or ()

        for cell, button in enumerate(self.board_buttons):
            mark = self.state.board[cell]
            text = mark if mark else str(cell)
            bg = PALETTE["surface"]
            fg = PALETTE["ink"]

            if cell in winning_line:
                bg = PALETTE["win"]
            elif mark:
                bg = PALETTE["occupied"]
                fg = PALETTE["primary_dark"] if mark == ROBOT else PALETTE["coral"]
            elif cell == self.selected_robot_cell:
                bg = PALETTE["selected"]
            elif cell in self.analyses:
                bg = CELL_COLORS[self.analyses[cell].category]

            button.configure(text=text, bg=bg, fg=fg)

        winner = self.state.winner()
        if winner == HUMAN:
            self.status_var.set("상태: 사람이 승리했습니다. 입력 동기화를 확인하세요.")
        elif winner == ROBOT:
            self.status_var.set("상태: 로봇이 승리했습니다.")
        elif self.state.is_draw():
            self.status_var.set("상태: 무승부입니다.")
        elif self.waiting_for_human:
            self.status_var.set("상태: 사람의 수를 보드에서 클릭하세요.")
        elif self.analyses:
            self.status_var.set("상태: 추천 색상을 확인하고 3번 추천 칸 선택을 누르세요.")
        else:
            self.status_var.set("상태: 로봇 차례입니다. 2번 다음 수 예측을 누르세요.")

        self.mode_var.set(self._mode_text())

    def _mode_text(self) -> str:
        mode = "실제 로봇" if not self.robot_dry_run else "Dry-run"
        connection = "연결됨" if self.robot_connected else "연결 필요"
        return f"모드: {mode} / {connection} / Port {self.robot_config.get('port', 'COM3')}"

    def _append_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n\n")
        self.log_text.see(tk.END)

    def _on_close(self) -> None:
        if hasattr(self.robot, "close"):
            self.robot.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TicTacToeRobotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
