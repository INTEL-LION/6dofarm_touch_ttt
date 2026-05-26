@echo off
cd /d "%~dp0"
set /p CELL=Cell number 0-8: 
python tools\touch_cell.py %CELL%

