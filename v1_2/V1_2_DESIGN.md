# v1.2 Design

## Name

`v1.2: coordinated smooth-motion pick-and-place tic-tac-toe`

## Problem Observed

v1.1 improved the route by adding a board-transit waypoint where servo 2 moves to 90 degrees.

However, movement still looked choppy in these transitions:

- `board transit holding -> cell hover holding`
- `cell hover holding -> cell approach/place holding`
- right before gripper open/release

The main cause is that v1.1 used joint step dividers. Heavy joints moved less frequently, but that can look like visible stepping.

## v1.2 Motion Strategy

v1.2 changes the Arduino motion planner:

- all joints share one time base
- every frame computes an interpolated target for every joint
- interpolation uses smootherstep easing
- heavy joints increase total duration instead of skipping updates
- gripper-only moves are staged slowly with settle delay

This should look smoother because the robot no longer pauses individual joints between skipped steps.

## Key Arduino Parameters

```cpp
const int FRAME_DELAY_MS = 20;
const int MIN_MOVE_DURATION_MS = 450;
const int MAX_MOVE_DURATION_MS = 6500;
const int HOLD_DELAY_MS = 220;
const int GRIPPER_FRAME_DELAY_MS = 35;
const int GRIPPER_SETTLE_DELAY_MS = 450;
const int JOINT_MS_PER_DEGREE[SERVOS] = {24, 38, 38, 28, 28, 18};
```

If movement is still too sharp:

- increase `JOINT_MS_PER_DEGREE` for servo 2 and 3
- increase `MIN_MOVE_DURATION_MS`
- increase `FRAME_DELAY_MS` only if CPU/servo behavior is unstable

If movement is too slow:

- decrease `JOINT_MS_PER_DEGREE`
- decrease `MAX_MOVE_DURATION_MS`

## Upload

```powershell
cd C:\Users\npgy2\.anaconda\intellion
.\run_upload_arduino_uno_v1_2.bat
```

## Python Compatibility

The serial command protocol is unchanged:

```text
M a,b,c,d,e,f
```

So the existing Python UI and tic-tac-toe logic can be used after uploading the v1.2 Arduino sketch.

## ROS2 Note

ROS2 is still optional. v1.2 focuses on motion quality. The ROS2 bridge skeleton from v1.1 can still be used later for telemetry, but it is not required for smoother motion.

