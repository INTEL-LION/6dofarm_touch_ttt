@echo off
cd /d "%~dp0"

set ARDUINO_CLI=C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe

if not exist "%ARDUINO_CLI%" (
  echo arduino-cli.exe was not found.
  echo Expected: %ARDUINO_CLI%
  echo Install Arduino IDE or edit this batch file.
  pause
  exit /b 1
)

echo Compiling Arduino Uno sketch...
"%ARDUINO_CLI%" compile -b arduino:avr:uno arduino\tictactoe_arm_serial
if errorlevel 1 goto error

echo Uploading to Arduino Uno on COM3...
"%ARDUINO_CLI%" upload -p COM3 -b arduino:avr:uno arduino\tictactoe_arm_serial
if errorlevel 1 goto error

echo Upload complete.
goto end

:error
echo Upload failed. Check COM port, board connection, and Arduino IDE serial monitor.
pause
exit /b 1

:end

