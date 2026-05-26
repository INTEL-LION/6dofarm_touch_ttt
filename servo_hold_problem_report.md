# Servo Hold Problem Report

## Symptom

When running a one-shot real movement command from the all-90-degree starting pose, the arm briefly loses holding force, drops under gravity, and then suddenly moves toward the selected touch cell.

## Confirmed Cause

The main cause is Arduino Uno auto-reset when the PC opens the serial port.

During reset and bootloader startup:

- The Arduino sketch is not running.
- Servo PWM signals are temporarily not being generated.
- The servos may stop actively holding position.
- A gravity-loaded robot arm can sag or collapse.
- After boot, the sketch starts again and the next motion command can look sudden.

This cannot be fully solved by Arduino code because no sketch code runs while the board is resetting.

## Software Mitigation Added

- The game UI now has a `Connect Robot` button.
- Real robot movement is blocked until the robot is connected.
- The serial connection is kept open after connection, so the Uno is not reset for every move.
- `touch_cell.py --real` is now blocked by default because it opens the port once and exits.
- Repeated real tests should use `tools/touch_cell_session.py`, which opens the port once and keeps it open.

## Remaining Limitation

The first serial connection can still reset the Uno on many Uno/CH340 boards. If the robot arm must hold itself up during that first connection, software alone cannot guarantee safety.

## Practical Fixes

Use at least one of these:

1. Physically support the arm while pressing `Connect Robot`, then remove support after connection.
2. Start the robot from a mechanically safe/resting pose where gravity cannot collapse it.
3. Disable Uno auto-reset after uploading the sketch, for example with a 10 uF capacitor between RESET and GND. Remove it when uploading new sketches.
4. Use an external servo controller that keeps PWM output stable independently of Arduino reset.
5. Use a servo power system with enough current so brownout does not reset the Arduino.

