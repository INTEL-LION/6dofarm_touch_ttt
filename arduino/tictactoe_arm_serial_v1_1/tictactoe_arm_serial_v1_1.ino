// v1.1 6-axis robot arm serial control for tic-tac-toe.
// Adds vibration-reduced motion, joint-specific speed limits,
// gripper settling, and smoother start/stop behavior.
//
// Protocol:
//   PING
//   H
//   Q
//   J 1,5
//   M 90,90,90,90,90,60
//
// Servo 6 is the gripper. It is clamped to 0..90 degrees.
// 90 = closed, lower values = more open.

#include <Servo.h>

const int SERVOS = 6;
const int BAUD_RATE = 9600;

// Lower base delay is not automatically faster because the profile adds
// extra delay near the beginning/end of a move.
const int BASE_STEP_DELAY_MS = 16;
const int EASE_EXTRA_DELAY_MS = 22;
const int HOLD_DELAY_MS = 180;
const int GRIPPER_SETTLE_DELAY_MS = 350;

// Larger values make a joint move less frequently. Shoulder/elbow are slower
// because they carry most of the gravity load and tend to excite vibration.
const int JOINT_STEP_DIVIDER[SERVOS] = {1, 2, 2, 1, 1, 1};

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
    Serial.println("OK PONG V1_1");
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
  int startAngle[SERVOS];
  int diff[SERVOS];
  int maxTicks = 0;
  bool gripperChanged = target[5] != currentAngle[5];

  for (int i = 0; i < SERVOS; i++) {
    startAngle[i] = currentAngle[i];
    diff[i] = abs(target[i] - currentAngle[i]);
    int ticks = diff[i] * JOINT_STEP_DIVIDER[i];
    if (ticks > maxTicks) {
      maxTicks = ticks;
    }
  }

  if (maxTicks == 0) {
    delay(HOLD_DELAY_MS);
    return;
  }

  for (int tick = 1; tick <= maxTicks; tick++) {
    for (int i = 0; i < SERVOS; i++) {
      if (tick % JOINT_STEP_DIVIDER[i] != 0) {
        continue;
      }

      if (currentAngle[i] < target[i]) {
        currentAngle[i]++;
        myservo[i].write(currentAngle[i]);
      } else if (currentAngle[i] > target[i]) {
        currentAngle[i]--;
        myservo[i].write(currentAngle[i]);
      }
    }

    delay(profileDelay(tick, maxTicks));
  }

  // Make sure all joints land exactly on the requested target.
  for (int i = 0; i < SERVOS; i++) {
    currentAngle[i] = target[i];
    myservo[i].write(currentAngle[i]);
  }

  delay(HOLD_DELAY_MS);
  if (gripperChanged) {
    delay(GRIPPER_SETTLE_DELAY_MS);
  }
}

int profileDelay(int tick, int maxTicks) {
  if (maxTicks <= 1) {
    return BASE_STEP_DELAY_MS + EASE_EXTRA_DELAY_MS;
  }

  int edge = tick;
  if (maxTicks - tick < edge) {
    edge = maxTicks - tick;
  }

  int ramp = maxTicks / 4;
  if (ramp < 1) {
    ramp = 1;
  }

  if (edge >= ramp) {
    return BASE_STEP_DELAY_MS;
  }

  int extra = map(ramp - edge, 0, ramp, 0, EASE_EXTRA_DELAY_MS);
  return BASE_STEP_DELAY_MS + extra;
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

