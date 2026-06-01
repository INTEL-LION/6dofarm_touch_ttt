#!/usr/bin/env bash
set -euo pipefail

mkdir -p ros2_bags

ros2 bag record -o ros2_bags/v1_3_last \
  /ttt/game_state \
  /ttt/recommended_move \
  /robot_arm/sequence_step \
  /robot_arm/target_servo_angles \
  /robot_arm/target_servo_angles_array \
  /robot_arm/event
