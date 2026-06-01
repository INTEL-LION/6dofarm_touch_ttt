# v1.3 Design

## Name

`v1.3: bag recording and servo-output analysis`

## Goal

v1.3 keeps the v1.2 smooth Arduino motion and adds a practical experiment-analysis layer.

The UI can now record one game into a local bag folder:

```text
bags/v1_3_bag_YYYYMMDD_HHMMSS/
  events.jsonl
  servo_steps.csv
  analysis.html
```

## UI Workflow

1. Run the normal UI.
2. Click `v1.3 Bag 기록 ON/OFF`.
3. Click `새 게임`.
4. Play normally: predict, select, and place robot moves.
5. Click `Bag 결과 시각화`.

The analysis page shows:

- target angle graph for servo 1-6
- yellow bands where v1.2 used 50% speed
- cell order
- sequence step names
- speed percent per step

## Recorded Topics

The local `events.jsonl` file stores events with ROS2-style topic names:

```text
/ttt/game_state
/ttt/recommended_move
/robot_arm/sequence_step
/robot_arm/target_servo_angles
/robot_arm/event
```

Servo angles are target/output commands from the PC to the Arduino. They are not measured feedback because the current servo arm has no encoder feedback.

## WSL ROS2 Replay

From WSL, go to the mounted project path and source ROS2:

```bash
cd /mnt/c/Users/npgy2/.anaconda/intellion
source /opt/ros/<distro>/setup.bash
python3 v1_3/ros2_bag_replay_v1_3.py --once
```

To create a real ROS2 bag while replaying, use two WSL terminals.

Terminal 1:

```bash
cd /mnt/c/Users/npgy2/.anaconda/intellion
source /opt/ros/<distro>/setup.bash
ros2 bag record -o ros2_bags/v1_3_last \
  /ttt/game_state \
  /ttt/recommended_move \
  /robot_arm/sequence_step \
  /robot_arm/target_servo_angles \
  /robot_arm/target_servo_angles_array \
  /robot_arm/event
```

Terminal 2:

```bash
cd /mnt/c/Users/npgy2/.anaconda/intellion
source /opt/ros/<distro>/setup.bash
python3 v1_3/ros2_bag_replay_v1_3.py --once
```

## ROS2 Graph Plotting

The replay bridge publishes numeric servo output as:

```text
/robot_arm/target_servo_angles_array
```

You can inspect it with:

```bash
ros2 topic echo /robot_arm/target_servo_angles_array
```

For plotting, use `rqt_plot` if installed:

```bash
rqt_plot /robot_arm/target_servo_angles_array/data[0] \
  /robot_arm/target_servo_angles_array/data[1] \
  /robot_arm/target_servo_angles_array/data[2] \
  /robot_arm/target_servo_angles_array/data[3] \
  /robot_arm/target_servo_angles_array/data[4] \
  /robot_arm/target_servo_angles_array/data[5]
```

