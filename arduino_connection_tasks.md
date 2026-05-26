# Arduino Uno Robot Arm Connection Tasks

## Control Direction

The PC does the tic-tac-toe calculation, board-state tracking, cell recommendation, and calibration storage.

The Arduino Uno only receives simple serial commands and moves the six servos. This is the right split because the Uno has limited memory and does not need to run minimax, UI logic, or board-state logic.

Arduino Serial Monitor is not required for the workflow below.

## Immediate Task Order

### 1. Upload the Arduino Sketch

Open this sketch in the Arduino IDE:

```text
arduino/tictactoe_arm_serial/tictactoe_arm_serial.ino
```

Upload it to the Arduino Uno.

The Arduino IDE is only used for upload. After upload, close Arduino Serial Monitor if it is open because only one program can normally hold the COM port at a time.

The sketch keeps the original servo pin mapping:

```text
servo 1 -> D3
servo 2 -> D2
servo 3 -> D9
servo 4 -> D8
servo 5 -> D4
servo 6 gripper -> D5
```

### 2. Check Power and Safety First

Do this before real movement:

- Use an external 5-6V servo power supply if the arm has multiple servos.
- Connect Arduino GND and servo power GND together.
- Keep USB connected for serial communication.
- Start with the arm away from the tic-tac-toe board.
- Keep one hand near the power switch.
- Do not let the gripper command exceed 90 degrees.

The included Arduino sketch clamps servo 6 to `0..90`.

### 3. Find the Windows COM Port

In Arduino IDE, check:

```text
Tools -> Port
```

Example:

```text
COM3
```

Put that port into:

```text
config/robot.json
```

Use:

```json
{
  "mode": "arduino_serial",
  "port": "COM3",
  "baud_rate": 9600,
  "timeout_seconds": 2,
  "move_delay_seconds": 0.5,
  "dry_run": true
}
```

### 4. Install Python Serial Support

Arduino serial mode needs `pyserial`:

```powershell
python -m pip install pyserial
```

### 5. Check Arduino Connection from Python

Do not use Arduino Serial Monitor.

Run:

```powershell
python tools/arduino_check.py
```

Or:

```powershell
.\run_arduino_check.bat
```

This sends `PING`, `Q`, `H`, and `Q` from Python and prints the Arduino responses.

### 6. Calibrate the Nine Board Cells from Python

Run:

```powershell
python tools/arduino_calibrator.py
```

Or:

```powershell
.\run_calibrator.bat
```

Use the GUI:

1. Close Arduino Serial Monitor.
2. Click `Connect`.
3. Use jog buttons to move one servo at a time.
4. Select cell `0..8`.
5. Move to a safe pose near the cell and click `Save Approach Pose`.
6. Move lightly to the cell center and click `Save Touch Pose`.
7. Repeat for all nine cells.

The tool writes directly to:

```text
config/calibration.json
```

### 7. Test the Game UI in Dry-Run

Keep this in `config/robot.json`:

```json
"dry_run": true
```

Run:

```powershell
python src/main.py
```

The UI should show the exact Arduino commands without moving the robot.

### 8. Enable Real Movement

Only after all nine cells are calibrated:

```json
"dry_run": false
```

Then test one cell at a time using the UI.

## Python Replaces Serial Monitor

The Arduino sketch still understands these serial commands:

- `PING`: connection check
- `Q`: print current servo angles
- `H`: move all servos to home angle
- `J 1,5`: move servo 1 by +5 degrees
- `J 1,-5`: move servo 1 by -5 degrees
- `M a,b,c,d,e,f`: move all six servos to target angles

But you do not type these into Arduino Serial Monitor. The Python tools send them.

## Important Gripper Rule

Servo 6 is the gripper:

- `90`: closed baseline
- Lower than `90`: opens the gripper
- Higher than `90`: tries to close beyond the already closed state

So the software and Arduino sketch both clamp servo 6 to a maximum of `90`.
