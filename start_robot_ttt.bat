@echo off
cd /d "%~dp0"

echo.
echo 6DOF Robot Arm Tic-Tac-Toe Starter
echo Project root: %cd%
echo.
echo [1] Install/check Python requirements
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo [2] Run software tests
python -m unittest discover tests
if errorlevel 1 goto error

echo.
echo [3] Validate calibration
python tools\validate_calibration.py
if errorlevel 1 goto error

echo.
echo [4] Check Arduino connection
python tools\arduino_check.py
if errorlevel 1 goto error

echo.
echo [5] Start UI
python src\main.py
goto end

:error
echo.
echo Startup stopped because one step failed.
echo Check the message above.
pause
exit /b 1

:end
echo.
echo Done.

