# v1.1 Design

## Name

`v1.1: vibration-reduced pick-and-place tic-tac-toe`

## Goal

Keep the v1 tic-tac-toe algorithm and calibration workflow, but improve real robot motion quality.

v1.1 is separated from v1 by using a new Arduino sketch:

```text
arduino/tictactoe_arm_serial_v1_1/tictactoe_arm_serial_v1_1.ino
```

## Applied Improvements

### 1. Vibration-Reduced Motion Profile

The v1 Arduino sketch moved every active servo by one degree at a fixed delay.

v1.1 adds:

- slower start
- faster middle section
- slower final approach
- exact final target write
- final hold delay

This reduces abrupt start/stop vibration.

### 2. Joint-Specific Speed Limits

The shoulder and elbow joints carry more load, so they are stepped less frequently:

```text
servo 1 base:          normal
servo 2 shoulder:      slower
servo 3 elbow:         slower
servo 4 wrist rotate:  normal
servo 5 wrist tilt:    normal
servo 6 gripper:       normal
```

The current Arduino setting is:

```cpp
const int JOINT_STEP_DIVIDER[SERVOS] = {1, 2, 2, 1, 1, 1};
```

### 3. Gripper Stabilization

When servo 6 changes, v1.1 adds a longer settle delay after the move.

This helps:

- avoid piece slip after pickup
- avoid piece bounce after release
- let the arm stop vibrating before the next waypoint

## How to Upload

```powershell
cd C:\Users\npgy2\.anaconda\intellion
.\run_upload_arduino_uno_v1_1.bat
```

## How to Run

The Python protocol is unchanged, so the existing UI can talk to v1.1 after the v1.1 sketch is uploaded.

```powershell
.\run_ui.bat
```

## ROS2 Check

ROS2 can be useful, but it should not be required for v1.1 operation.

Good ROS2 features for this project:

- publish current tic-tac-toe board state
- publish selected target cell
- publish current sequence step
- publish current/target servo angles
- publish robot mode: dry-run, real, connected
- record motion sessions to a rosbag
- view state in Foxglove Studio

Less useful for v1.1:

- full inverse kinematics without a measured robot model
- RViz URDF visualization before link lengths/axes are measured

Recommended path:

```text
v1.1: motion stability
v1.2: optional ROS2 telemetry bridge
v1.3: measured link model / URDF / RViz
```

## ROS2 Topic Proposal

```text
/ttt/board_state         std_msgs/String
/ttt/target_cell         std_msgs/Int32
/robot_arm/mode          std_msgs/String
/robot_arm/sequence_step std_msgs/String
/robot_arm/servo_angles  std_msgs/String
/robot_arm/event         std_msgs/String
```

Use JSON strings at first to avoid custom message packages.

