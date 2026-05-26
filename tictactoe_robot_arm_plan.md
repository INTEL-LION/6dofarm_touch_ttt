# 6-Axis Robot Arm Tic-Tac-Toe Plan

## Goal

Build a tic-tac-toe assistant that uses a 6-axis robot arm to touch a selected square on a physical board. The robot does not place pieces itself. A human places the actual mark after the robot touches the target cell.

The computer keeps the game state, calculates winning or non-losing moves, visually recommends candidate cells, and sends the chosen cell coordinate to the robot arm.

## Core Assumptions

- The robot arm has no reliable motor position feedback.
- The tic-tac-toe board is fixed in front of the robot arm.
- The board location does not move during a game.
- The robot only needs to touch one of nine predefined cells.
- The human enters the opponent's move into the computer UI.
- The human places the robot player's mark on the physical board after the robot touches a cell.
- Safety matters more than speed.

## System Architecture

### 1. Game State Module

Responsibilities:

- Store the 3x3 board state.
- Track whose turn it is.
- Validate legal moves.
- Detect win, draw, or ongoing state.
- Reset the game.

Board representation:

```text
0 | 1 | 2
3 | 4 | 5
6 | 7 | 8
```

Recommended internal values:

- `EMPTY`
- `HUMAN`
- `ROBOT`

### 2. Tic-Tac-Toe Decision Algorithm

Use minimax because tic-tac-toe is small and completely solvable.

Move priority:

1. Win immediately if possible.
2. Block the opponent's immediate win.
3. Choose a minimax optimal move.
4. Prefer center, then corners, then edges when multiple moves have the same score.

The UI should classify available cells:

- Best winning move
- Forced blocking move
- Safe draw or non-losing move
- Risky move that may lose
- Illegal occupied cell

### 3. Visual UI Module

Responsibilities:

- Display the current board.
- Let the user enter the opponent's move.
- Show recommended robot moves visually.
- Let the user choose one recommended cell.
- Send the selected cell to the robot control module.

Useful visual states:

- Green: winning move
- Blue: safe or draw-guaranteed move
- Yellow: necessary block
- Red: losing or risky move
- Gray: occupied cell

The UI should not assume computer vision. The human is responsible for keeping the digital board synced with the real board.

### 4. Board Calibration Module

Because there is no motor feedback, the first version should use fixed, calibrated robot poses.

Calibration steps:

1. Mount the tic-tac-toe board in a fixed location.
2. Define a safe home pose.
3. Manually move or command the robot to touch each of the nine cell centers.
4. Save each cell's robot pose.
5. Test each saved pose slowly.
6. Add an approach pose above each cell before the final touch pose.

Each cell should have:

- `approach_pose`: a safe pose slightly above or away from the board.
- `touch_pose`: the pose that lightly touches the target square.
- `retreat_pose`: usually same as approach pose.

Example structure:

```json
{
  "0": {
    "approach_pose": [0, 0, 0, 0, 0, 0],
    "touch_pose": [0, 0, 0, 0, 0, 0]
  }
}
```

### 5. Robot Motion Module

Responsibilities:

- Move to home pose.
- Move to a selected cell's approach pose.
- Move slowly to the touch pose.
- Pause briefly.
- Return to approach pose.
- Return to home pose.

Basic motion sequence:

```text
home -> cell approach -> cell touch -> pause -> cell approach -> home
```

Because there is no feedback:

- Use slow movement.
- Use conservative acceleration.
- Avoid sweeping across the board surface.
- Add a physical emergency stop.
- Use soft touch materials if possible.
- Recalibrate if the board or arm base moves.

## First Prototype Scope

### Phase 1: Software-Only Tic-Tac-Toe

Deliverables:

- Board state logic.
- Win/draw detection.
- Minimax algorithm.
- CLI or simple GUI for human move input.
- Visual recommendation of best moves.

Acceptance test:

- The robot player never loses when the human enters valid moves.

### Phase 2: Calibration Data Format

Deliverables:

- `calibration.json` containing nine cell poses.
- Load/save calibration logic.
- Dry-run mode that prints the selected cell and pose without moving the robot.

Acceptance test:

- Selecting cell `0` to `8` reliably maps to the intended saved pose.

### Phase 3: Robot Arm Touch Execution

Deliverables:

- Robot connection wrapper.
- Home, approach, touch, retreat sequence.
- Speed and acceleration limits.
- Manual confirmation before each real movement.

Acceptance test:

- The robot can touch each cell center slowly and return home.

### Phase 4: Integrated Game Loop

Deliverables:

- Human inputs opponent move.
- Algorithm recommends robot moves.
- User selects a recommended move.
- Robot touches selected cell.
- User places the robot mark on the physical board.
- Digital board updates.

Acceptance test:

- A full physical tic-tac-toe game can be played without the robot losing.

## Suggested Project Structure

```text
intellion/
  tictactoe_robot_arm_plan.md
  src/
    main.py
    game.py
    ai.py
    calibration.py
    robot_arm.py
  config/
    calibration.example.json
    calibration.json
  tests/
    test_game.py
    test_ai.py
```

## Algorithm Sketch

```text
start game
while game is not finished:
    user enters human move
    update board
    check game result

    calculate all robot candidate moves
    classify moves visually
    user selects robot move

    send selected cell to robot arm
    robot touches selected cell
    human places robot mark
    update board
    check game result
```

## Key Risks

- Board movement after calibration causes inaccurate touches.
- No motor feedback means missed steps or drift may not be detected.
- Human may enter a move incorrectly in the UI.
- Robot may touch too hard if the board is not positioned correctly.

## Risk Controls

- Add a fixed board mount.
- Add clear cell labels matching the UI.
- Start every move from home pose.
- Add dry-run mode.
- Add manual confirmation before physical movement.
- Keep touch speed low.
- Add emergency stop hardware.
- Add a reset and resync flow when digital and physical boards differ.

## Next Implementation Step

Start with the software-only version:

1. Implement board state and minimax.
2. Build a simple visual board UI.
3. Add move classification.
4. Add a mock robot module that prints target cell coordinates.
5. Replace the mock robot with the real robot API after calibration.
