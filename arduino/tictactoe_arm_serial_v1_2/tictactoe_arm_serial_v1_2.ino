// v1.2 6-axis robot arm serial control for tic-tac-toe.
// Focus: smoother motion with coordinated S-curve interpolation.
//
// Compared with v1.1:
// - removes step-divider motion that could look choppy
// - updates all joints on a shared time base
// - uses smoothstep easing for start/stop
// - uses per-joint motion duration weights instead of skipped steps
// - adds staged gripper-only moves with settle time
//
// Protocol:
//   PING
//   H
//   Q
//   J 1,5
//   M 90,90,90,90,90,60

#include <Servo.h>

const int SERVOS = 6;
const int BAUD_RATE = 9600;

const int FRAME_DELAY_MS = 20;
const int MIN_MOVE_DURATION_MS = 450;
const int MAX_MOVE_DURATION_MS = 6500;
const int HOLD_DELAY_MS = 220;
const int GRIPPER_FRAME_DELAY_MS = 35;
const int GRIPPER_SETTLE_DELAY_MS = 450;

// Heavier joints do not skip frames. Instead, they make the whole move's
// duration longer when they travel far.
const int JOINT_MS_PER_DEGREE[SERVOS] = {24, 38, 38, 28, 28, 18};

int PIN[SERVOS] = {3, 2, 9, 8, 4, 5};
int MIN_ANGLE[SERVOS] = {0, 0, 0, 0, 0, 0};
int MAX_ANGLE[SERVOS] = {180, 180, 180, 180, 180, 90};
int HOME_ANGLE[SERVOS] = {90, 90, 90, 90, 90, 90};
int currentAngle[SERVOS] = {90, 90, 90, 90, 90, 90};

Servo myservo[SERVOS];

void setup() {
  Serial.begin(BAUD_RATE);

  for (int i = 0; i < SERVOS; i++) {
    myservo[i].attach(PIN[i]);
    myservo[i].write(HOME_ANGLE[i]);
    currentAngle[i] = HOME_ANGLE[i];
  }

  delay(500);
}

void loop() {
  if (!Serial.available()) {
    return;
  }

  String line = Serial.readStringUntil('\n');
  line.trim();

  if (line.length() == 0) {
    return;
  }

  if (line == "PING") {
    Serial.println("OK PONG V1_2");
    return;
  }

  if (line == "H") {
    moveToAngles(HOME_ANGLE);
    Serial.println("OK HOME");
    return;
  }

  if (line == "Q") {
    printCurrentAngles();
    return;
  }

  if (line.startsWith("J ")) {
    bool parsed = jogServo(line.substring(2));
    if (!parsed) {
      Serial.println("ERR BAD_JOG");
      return;
    }
    printCurrentAngles();
    return;
  }

  if (line.startsWith("M ")) {
    int target[SERVOS];
    bool parsed = parseMoveCommand(line.substring(2), target);
    if (!parsed) {
      Serial.println("ERR BAD_MOVE");
      return;
    }

    moveToAngles(target);
    Serial.println("OK MOVE");
    return;
  }

  Serial.println("ERR UNKNOWN_COMMAND");
}

bool jogServo(String payload) {
  int comma = payload.indexOf(',');
  if (comma < 0) {
    return false;
  }

  String servoToken = payload.substring(0, comma);
  String deltaToken = payload.substring(comma + 1);
  servoToken.trim();
  deltaToken.trim();

  int servoNumber = servoToken.toInt();
  int delta = deltaToken.toInt();

  if (servoNumber < 1 || servoNumber > SERVOS) {
    return false;
  }

  int index = servoNumber - 1;
  int target = clampAngle(index, currentAngle[index] + delta);
  currentAngle[index] = target;
  myservo[index].write(currentAngle[index]);
  delay(HOLD_DELAY_MS);
  return true;
}

bool parseMoveCommand(String payload, int target[]) {
  int start = 0;

  for (int i = 0; i < SERVOS; i++) {
    int comma = payload.indexOf(',', start);
    String token;

    if (i == SERVOS - 1) {
      token = payload.substring(start);
    } else {
      if (comma < 0) {
        return false;
      }
      token = payload.substring(start, comma);
      start = comma + 1;
    }

    token.trim();
    if (token.length() == 0) {
      return false;
    }

    int angle = token.toInt();
    target[i] = clampAngle(i, angle);
  }

  return true;
}

int clampAngle(int servoIndex, int angle) {
  if (angle < MIN_ANGLE[servoIndex]) {
    return MIN_ANGLE[servoIndex];
  }
  if (angle > MAX_ANGLE[servoIndex]) {
    return MAX_ANGLE[servoIndex];
  }
  return angle;
}

void moveToAngles(int target[]) {
  if (allAtTarget(target)) {
    delay(HOLD_DELAY_MS);
    return;
  }

  if (isOnlyGripperMove(target)) {
    moveGripperOnly(target[5]);
    return;
  }

  int startAngle[SERVOS];
  int delta[SERVOS];
  int lastWritten[SERVOS];
  int duration = MIN_MOVE_DURATION_MS;

  for (int i = 0; i < SERVOS; i++) {
    startAngle[i] = currentAngle[i];
    delta[i] = target[i] - startAngle[i];
    lastWritten[i] = currentAngle[i];

    int weighted = abs(delta[i]) * JOINT_MS_PER_DEGREE[i];
    if (weighted > duration) {
      duration = weighted;
    }
  }

  if (duration > MAX_MOVE_DURATION_MS) {
    duration = MAX_MOVE_DURATION_MS;
  }

  int frames = duration / FRAME_DELAY_MS;
  if (frames < 1) {
    frames = 1;
  }

  for (int frame = 1; frame <= frames; frame++) {
    float progress = (float)frame / (float)frames;
    float eased = smootherstep(progress);

    for (int i = 0; i < SERVOS; i++) {
      int angle = (int)round((float)startAngle[i] + ((float)delta[i] * eased));
      angle = clampAngle(i, angle);
      if (angle != lastWritten[i]) {
        myservo[i].write(angle);
        lastWritten[i] = angle;
      }
    }

    delay(FRAME_DELAY_MS);
  }

  for (int i = 0; i < SERVOS; i++) {
    currentAngle[i] = target[i];
    myservo[i].write(currentAngle[i]);
  }

  delay(HOLD_DELAY_MS);
  if (target[5] != startAngle[5]) {
    delay(GRIPPER_SETTLE_DELAY_MS);
  }
}

bool allAtTarget(int target[]) {
  for (int i = 0; i < SERVOS; i++) {
    if (currentAngle[i] != target[i]) {
      return false;
    }
  }
  return true;
}

bool isOnlyGripperMove(int target[]) {
  for (int i = 0; i < SERVOS - 1; i++) {
    if (currentAngle[i] != target[i]) {
      return false;
    }
  }
  return currentAngle[5] != target[5];
}

void moveGripperOnly(int targetAngle) {
  targetAngle = clampAngle(5, targetAngle);

  while (currentAngle[5] != targetAngle) {
    if (currentAngle[5] < targetAngle) {
      currentAngle[5]++;
    } else {
      currentAngle[5]--;
    }
    myservo[5].write(currentAngle[5]);
    delay(GRIPPER_FRAME_DELAY_MS);
  }

  delay(GRIPPER_SETTLE_DELAY_MS);
}

float smootherstep(float x) {
  if (x <= 0.0) {
    return 0.0;
  }
  if (x >= 1.0) {
    return 1.0;
  }

  // 6x^5 - 15x^4 + 10x^3
  return x * x * x * (x * (x * 6.0 - 15.0) + 10.0);
}

void printCurrentAngles() {
  Serial.print("OK ANGLES ");
  for (int i = 0; i < SERVOS; i++) {
    if (i > 0) {
      Serial.print(",");
    }
    Serial.print(currentAngle[i]);
  }
  Serial.println();
}

