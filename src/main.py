from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from ai import MoveAnalysis, analyze_moves, choose_best_move
from calibration import load_calibration
from game import HUMAN, ROBOT, GameState
from robot_arm import create_robot_arm, load_robot_config
from session_bag import (
    SessionBagRecorder,
    list_bag_directories,
    open_existing_bag_analysis,
    read_servo_rows_from_directory,
)


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
        self.root.title("6축 로봇팔 틱택토 v1.3")
        self.state = GameState()
        self.calibration = load_calibration()
        self.robot_config = load_robot_config()
        self.robot = create_robot_arm(self.robot_config)
        self.robot_dry_run = bool(self.robot_config.get("dry_run", True))
        self.robot_connected = self.robot_dry_run
        self.analyses: dict[int, MoveAnalysis] = {}
        self.selected_robot_cell: int | None = None
        self.waiting_for_human = True
        self.bag_recorder = SessionBagRecorder()
        self.bag_requested = False

        self.status_var = tk.StringVar()
        self.selected_var = tk.StringVar(value="선택된 로봇 칸: 없음")
        self.mode_var = tk.StringVar(value=self._mode_text())
        self.bag_var = tk.StringVar(value="v1.3 bag: off")

        self.board_buttons: list[tk.Button] = []
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh()

    def _build_ui(self) -> None:
        self.root.geometry("1180x740")
        self.root.minsize(1040, 680)
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
            font=("Malgun Gothic", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            left,
            text="사람은 O, 로봇은 X입니다. v1.3은 로봇 동작을 bag으로 기록하고 분석합니다.",
            bg=PALETTE["bg"],
            fg=PALETTE["muted"],
            font=("Malgun Gothic", 11),
        ).pack(anchor="w", pady=(2, 14))

        board_frame = tk.Frame(left, bg=PALETTE["board"], padx=8, pady=8)
        board_frame.pack(anchor="w")

        for cell in range(9):
            button = tk.Button(
                board_frame,
                text=str(cell),
                width=6,
                height=3,
                font=("Malgun Gothic", 30, "bold"),
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
        tk.Label(info, textvariable=self.status_var, bg=PALETTE["bg"], fg=PALETTE["ink"], font=("Malgun Gothic", 13, "bold")).pack(anchor="w")
        tk.Label(info, textvariable=self.selected_var, bg=PALETTE["bg"], fg=PALETTE["teal"], font=("Malgun Gothic", 12)).pack(anchor="w", pady=(5, 0))
        tk.Label(info, textvariable=self.mode_var, bg=PALETTE["bg"], fg=PALETTE["muted"], font=("Malgun Gothic", 10)).pack(anchor="w", pady=(5, 0))
        tk.Label(info, textvariable=self.bag_var, bg=PALETTE["bg"], fg=PALETTE["primary_dark"], font=("Consolas", 10, "bold")).pack(anchor="w", pady=(5, 0))

        legend = tk.Frame(left, bg=PALETTE["bg"])
        legend.pack(anchor="w", pady=(4, 0))
        for label, color in (
            ("승리", CELL_COLORS["win"]),
            ("차단", CELL_COLORS["block"]),
            ("안전", CELL_COLORS["safe"]),
            ("위험", CELL_COLORS["risk"]),
        ):
            tk.Label(legend, text=f"  {label}  ", bg=color, fg=PALETTE["ink"], font=("Malgun Gothic", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(right, text="실행 순서", bg=PALETTE["surface"], fg=PALETTE["ink"], font=("Malgun Gothic", 18, "bold")).pack(anchor="w")
        tk.Label(
            right,
            text="bag 기록을 켠 뒤 새 게임을 시작하면 한 판의 동작이 분석 파일로 저장됩니다.",
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
            font=("Malgun Gothic", 10),
        ).pack(anchor="w", pady=(0, 10))

        actions = tk.Frame(right, bg=PALETTE["surface"])
        actions.pack(fill=tk.X)
        self._action_button(actions, "1. 로봇 연결", self._connect_robot, PALETTE["primary"]).pack(fill=tk.X, pady=4)
        self._action_button(actions, "2. 다음 수 예측", self._predict_robot_move, PALETTE["teal"]).pack(fill=tk.X, pady=4)
        self._action_button(actions, "3. 추천 칸 선택", self._select_recommended_robot_move, PALETTE["coral"]).pack(fill=tk.X, pady=4)
        self._action_button(actions, "4. 선택 칸에 말 놓기", self._execute_robot_touch, PALETTE["primary_dark"]).pack(fill=tk.X, pady=4)

        utility = tk.Frame(right, bg=PALETTE["surface"], pady=8)
        utility.pack(fill=tk.X)
        self._secondary_button(utility, "Bag Folder", self._choose_bag_folder).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "Open Saved Bag", self._open_saved_bag_browser).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "로봇 선공 준비", self._prepare_robot_first).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "전체 보정 좌표 확인", self._show_all_calibration).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "v1.3 Bag 기록 ON/OFF", self._toggle_bag_recording).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "Bag 결과 시각화", self._show_bag_analysis).pack(fill=tk.X, pady=3)
        self._secondary_button(utility, "새 게임", self._new_game).pack(fill=tk.X, pady=3)

        tk.Label(right, text="로봇 로그", bg=PALETTE["surface"], fg=PALETTE["ink"], font=("Malgun Gothic", 14, "bold")).pack(anchor="w", pady=(14, 5))
        self.log_text = tk.Text(
            right,
            width=46,
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
            font=("Malgun Gothic", 12, "bold"),
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
            font=("Malgun Gothic", 10, "bold"),
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
            self.bag_recorder.record_game_state(self.state.board, "robot", "human_move")
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
        self.bag_recorder.record_game_state(self.state.board, "robot", "robot_first_prepared")
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
        best = choose_best_move(self.state)
        self.bag_recorder.record_recommended_move(best, self.analyses)
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
        self.bag_recorder.record_recommended_move(best, self.analyses)
        self._refresh()

    def _execute_robot_touch(self) -> None:
        if self.selected_robot_cell is None:
            messagebox.showinfo("선택 필요", "3번 추천 칸 선택을 먼저 누르세요.")
            return
        if not self.robot_dry_run and not self.robot_connected:
            messagebox.showerror("로봇 미연결", "로봇팔을 받친 상태에서 1번 로봇 연결을 먼저 누르세요.")
            return

        cell = self.selected_robot_cell
        try:
            result = self.robot.touch_cell(cell, self.calibration, dry_run=self.robot_dry_run)
        except Exception as exc:
            messagebox.showerror("로봇 연결 오류", str(exc))
            return
        self._append_log(result.message)
        self.bag_recorder.record_robot_steps(cell, result.steps or [], result.message)

        try:
            self.state.make_move(cell, ROBOT)
        except ValueError as exc:
            messagebox.showwarning("로봇 수 오류", str(exc))
            return

        self.selected_robot_cell = None
        self.analyses = {}
        self.waiting_for_human = not self.state.is_finished()
        self.selected_var.set("선택된 로봇 칸: 없음")
        self.bag_recorder.record_game_state(self.state.board, "human", "robot_move")
        self._refresh()

    def _new_game(self) -> None:
        if self.bag_requested:
            if not self._start_new_bag():
                self.bag_requested = False
                self.bag_var.set("v1.3 bag: off")
        self.state.reset()
        self.analyses = {}
        self.selected_robot_cell = None
        self.waiting_for_human = True
        self.selected_var.set("선택된 로봇 칸: 없음")
        self._append_log("New game started.")
        self.bag_recorder.record_game_state(self.state.board, "human", "new_game")
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

    def _toggle_bag_recording(self) -> None:
        if self.bag_recorder.enabled:
            paths = self.bag_recorder.stop()
            self.bag_requested = False
            self.bag_var.set("v1.3 bag: off")
            if paths:
                self._append_log(f"v1.3 bag saved: {paths.directory}")
            return

        if not self._start_new_bag():
            self.bag_requested = False
            self.bag_var.set("v1.3 bag: off")
            return
        self.bag_requested = True
        turn = "human" if self.waiting_for_human else "robot"
        self.bag_recorder.record_game_state(self.state.board, turn, "bag_enabled")

    def _start_new_bag(self) -> bool:
        if self.bag_recorder.enabled:
            self.bag_recorder.stop()
        default_name = f"ttt_game_{self.state.board.count(ROBOT) + 1}"
        name = simpledialog.askstring("Bag name", "Name this bag:", parent=self.root, initialvalue=default_name)
        if name is None:
            return False
        paths = self.bag_recorder.start(name)
        self.bag_var.set(f"v1.3 bag: {paths.directory.name}")
        self._append_log(f"v1.3 bag recording started: {paths.directory}")
        return True

    def _show_bag_analysis(self) -> None:
        if not self.bag_recorder.paths:
            messagebox.showinfo("Bag 없음", "먼저 v1.3 Bag 기록을 켜고 게임을 진행하세요.")
            return
        html_path = self.bag_recorder.open_analysis()
        try:
            rows = read_servo_rows_from_directory(self.bag_recorder.paths.directory)
        except Exception as exc:
            messagebox.showerror("Bag 분석 오류", str(exc))
            return
        self._show_bag_graph_window(self.bag_recorder.paths.directory.name, rows)
        if html_path:
            self._append_log(f"v1.3 bag analysis refreshed: {html_path}")

    def _choose_bag_folder(self) -> None:
        if self.bag_recorder.enabled:
            messagebox.showinfo("Bag recording", "현재 bag 기록을 먼저 끈 뒤 저장 폴더를 바꾸세요.")
            return
        folder = filedialog.askdirectory(
            parent=self.root,
            title="Bag 저장 폴더 선택",
            initialdir=str(self.bag_recorder.root),
        )
        if not folder:
            return
        self.bag_recorder.set_root(Path(folder))
        self.bag_var.set(f"v1.3 bag folder: {self.bag_recorder.root}")
        self._append_log(f"v1.3 bag folder set: {self.bag_recorder.root}")

    def _open_saved_bag_browser(self) -> None:
        bags = list_bag_directories(self.bag_recorder.root)
        if not bags:
            messagebox.showinfo("저장된 Bag 없음", f"{self.bag_recorder.root} 안에 bag 폴더가 없습니다.")
            return

        window = tk.Toplevel(self.root)
        window.title("저장된 v1.3 Bag")
        window.geometry("640x420")
        window.configure(bg=PALETTE["surface"])

        tk.Label(
            window,
            text=f"Folder: {self.bag_recorder.root}",
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
            font=("Consolas", 9),
            wraplength=600,
            justify=tk.LEFT,
        ).pack(fill=tk.X, padx=14, pady=(14, 6))

        listbox = tk.Listbox(window, font=("Consolas", 11), height=14)
        listbox.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)
        for bag in bags:
            listbox.insert(tk.END, bag.name)

        def open_selected() -> None:
            selected = listbox.curselection()
            if not selected:
                return
            bag_dir = bags[selected[0]]
            try:
                open_existing_bag_analysis(bag_dir)
                rows = read_servo_rows_from_directory(bag_dir)
            except Exception as exc:
                messagebox.showerror("Bag 열기 오류", str(exc))
                return
            self._show_bag_graph_window(bag_dir.name, rows)
            self._append_log(f"opened saved bag graph: {bag_dir}")

        button_row = tk.Frame(window, bg=PALETTE["surface"])
        button_row.pack(fill=tk.X, padx=14, pady=(0, 14))
        self._secondary_button(button_row, "Open Graph", open_selected).pack(side=tk.LEFT, padx=(0, 8))
        self._secondary_button(button_row, "Close", window.destroy).pack(side=tk.LEFT)
        listbox.bind("<Double-Button-1>", lambda _event: open_selected())

    def _show_bag_graph_window(self, title: str, rows: list[dict[str, str]]) -> None:
        if not rows:
            messagebox.showinfo("Bag 비어 있음", "아직 기록된 servo step이 없습니다.")
            return

        window = tk.Toplevel(self.root)
        window.title(f"Bag Graph - {title}")
        window.geometry("1180x760")
        window.configure(bg="#f8fafc")

        tk.Label(
            window,
            text=f"v1.3 Bag Analysis: {title}",
            bg="#f8fafc",
            fg=PALETTE["ink"],
            font=("Malgun Gothic", 18, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(
            window,
            text="노란 배경은 50% 속도 구간입니다. 값은 Arduino로 보낸 목표 각도입니다.",
            bg="#f8fafc",
            fg=PALETTE["muted"],
            font=("Malgun Gothic", 10),
        ).pack(anchor="w", padx=18, pady=(0, 10))

        canvas = tk.Canvas(window, bg="#ffffff", height=430, highlightthickness=1, highlightbackground="#dbe4ee")
        canvas.pack(fill=tk.X, padx=18, pady=(0, 12))
        self._draw_servo_canvas(canvas, rows)

        table_frame = tk.Frame(window, bg="#ffffff", highlightthickness=1, highlightbackground="#dbe4ee")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
        header = "Step   Cell   Speed   Name                         S1   S2   S3   S4   S5   Grip"
        tk.Label(table_frame, text=header, bg="#eef6f8", fg=PALETTE["ink"], font=("Consolas", 10, "bold"), anchor="w").pack(fill=tk.X)
        text = tk.Text(table_frame, height=10, bg="#ffffff", fg=PALETTE["ink"], font=("Consolas", 10), relief=tk.FLAT)
        text.pack(fill=tk.BOTH, expand=True)
        for row in rows:
            line = (
                f"{row['step']:>4}   {row['cell']:>4}   {row['speed_percent']:>5}%   "
                f"{row['name'][:28]:<28} "
                f"{row['servo1']:>4} {row['servo2']:>4} {row['servo3']:>4} "
                f"{row['servo4']:>4} {row['servo5']:>4} {row['servo6_gripper']:>5}\n"
            )
            text.insert(tk.END, line)
        text.configure(state=tk.DISABLED)

    def _draw_servo_canvas(self, canvas: tk.Canvas, rows: list[dict[str, str]]) -> None:
        width = 1120
        height = 430
        left = 58
        right = 28
        top = 30
        bottom = 92
        plot_w = width - left - right
        plot_h = height - top - bottom
        max_x = max(1, len(rows) - 1)
        colors = ["#2563eb", "#0f766e", "#f97316", "#7c3aed", "#dc2626", "#111827"]

        canvas.configure(scrollregion=(0, 0, width, height))
        for angle in range(0, 181, 30):
            y = top + plot_h - (plot_h * angle / 180)
            canvas.create_line(left, y, width - right, y, fill="#e2e8f0")
            canvas.create_text(28, y, text=str(angle), fill="#64748b", font=("Consolas", 9))

        def x_at(index: int) -> float:
            return left + (plot_w * index / max_x)

        def y_at(value: float) -> float:
            return top + plot_h - (plot_h * value / 180.0)

        for index, row in enumerate(rows):
            if float(row["speed_percent"]) < 100:
                x = x_at(index)
                canvas.create_rectangle(x - 10, top, x + 10, top + plot_h, fill="#fde68a", outline="", stipple="gray25")

        for servo_index, color in enumerate(colors, start=1):
            key = "servo6_gripper" if servo_index == 6 else f"servo{servo_index}"
            points: list[float] = []
            for index, row in enumerate(rows):
                points.extend([x_at(index), y_at(float(row[key]))])
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=3, smooth=True)
            for index, row in enumerate(rows):
                canvas.create_oval(x_at(index) - 3, y_at(float(row[key])) - 3, x_at(index) + 3, y_at(float(row[key])) + 3, fill=color, outline=color)
            canvas.create_text(left + (servo_index - 1) * 145, 14, text=key, fill=color, font=("Consolas", 10, "bold"), anchor="w")

        canvas.create_line(left, top, left, top + plot_h, fill="#334155")
        canvas.create_line(left, top + plot_h, width - right, top + plot_h, fill="#334155")
        for index, row in enumerate(rows):
            x = x_at(index)
            canvas.create_line(x, top + plot_h, x, top + plot_h + 5, fill="#94a3b8")
            label = f"{row['step']}.C{row['cell']} {row['name'][:12]}"
            canvas.create_text(x, top + plot_h + 24, text=label, angle=35, fill="#475569", font=("Consolas", 8), anchor="nw")

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
            self.status_var.set("상태: 사람이 이겼습니다. 입력 순서를 확인하세요.")
        elif winner == ROBOT:
            self.status_var.set("상태: 로봇이 이겼습니다.")
        elif self.state.is_draw():
            self.status_var.set("상태: 무승부입니다.")
        elif self.waiting_for_human:
            self.status_var.set("상태: 사람이 수를 보드에서 클릭하세요.")
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
        if self.bag_recorder.enabled:
            self.bag_recorder.stop()
        if hasattr(self.robot, "close"):
            self.robot.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TicTacToeRobotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
