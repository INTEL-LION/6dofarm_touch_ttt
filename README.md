# 6-Axis Robot Arm Tic-Tac-Toe

This project controls a tic-tac-toe workflow where the computer calculates the robot move and a 6-axis robot arm only touches the selected physical board cell.

The current improved version can also run a pick-and-place path: it opens the gripper at the piece source, picks a mark, moves to the selected cell, releases the mark, and returns home.

## Run the UI

```powershell
python src/main.py
```

On Windows, you can also run:

```powershell
.\run_ui.bat
```

## Run Tests

```powershell
python -m unittest discover tests
```

Or:

```powershell
.\run_tests.bat
```

## Flow

1. Connect the robot first.
2. Predict the next robot move.
3. Select the recommended cell.
4. Touch the selected cell with the robot.
5. Place the robot's physical mark on the board by hand.

For robot-first play, start from an empty board and use `로봇 선공 준비`, then continue with prediction, selection, and touch.

Use `전체 보정 좌표 확인` in the UI to dry-run all nine calibrated cell mappings.

## Marks

- Human: `O`
- Robot: `X`

## Calibration

Edit `config/calibration.json` after measuring the real robot poses.

Each cell has:

- `approach_pose`: safe pose near the cell
- `touch_pose`: light touch pose at the cell center

The current robot module is a dry-run mock. Replace `MockRobotArm` with the real robot API after calibration and safety checks.

## Arduino Uno Servo Arm

For the real Arduino Uno arm, use:

```text
arduino/tictactoe_arm_serial/tictactoe_arm_serial.ino
```

Then follow:

```text
arduino_connection_tasks.md
```

The PC calculates the tic-tac-toe move and sends only six servo angles to the Arduino.

To upload the included Uno sketch on this Windows setup:

```powershell
.\run_upload_arduino_uno.bat
```

Arduino Serial Monitor is not needed after upload. Use these Python tools instead:

```powershell
python tools/arduino_check.py
python tools/arduino_calibrator.py
```

Or:

```powershell
.\run_arduino_check.bat
.\run_calibrator.bat
```

After calibration:

```powershell
python tools/validate_calibration.py
python tools/touch_cell.py 4
python tools/touch_cell.py 4 --real --allow-reset-risk
```

`touch_cell.py` uses dry-run unless `--real` is passed. One-shot real movement is blocked unless `--allow-reset-risk` is passed because opening the serial port can reset the Uno.
For repeated real movement tests, prefer the persistent session so the Uno is not reset for every cell:

```powershell
python tools/touch_cell_session.py
```

Switch the game UI between command-only and real robot movement:

```powershell
python tools/set_robot_mode.py dry-run
python tools/set_robot_mode.py real
```
