// 6-axis robot arm serial control for tic-tac-toe.
// Based on the Scipia Arduino Uno servo arm example.
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
const int STEP_DELAY_MS = 35;
const int HOLD_DELAY_MS = 150;

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
    Serial.println("OK PONG");
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
  myservo[index].write(target);
  currentAngle[index] = target;
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
  bool moving = true;

  while (moving) {
    moving = false;

    for (int i = 0; i < SERVOS; i++) {
      if (currentAngle[i] < target[i]) {
        currentAngle[i]++;
        myservo[i].write(currentAngle[i]);
        moving = true;
      } else if (currentAngle[i] > target[i]) {
        currentAngle[i]--;
        myservo[i].write(currentAngle[i]);
        moving = true;
      }
    }

    delay(STEP_DELAY_MS);
  }

  for (int i = 0; i < SERVOS; i++) {
    myservo[i].write(currentAngle[i]);
  }
  delay(HOLD_DELAY_MS);
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
