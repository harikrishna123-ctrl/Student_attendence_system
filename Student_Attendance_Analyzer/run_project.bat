@echo off
title Student Attendance Analyzer Using Set Theory - Sandip University
color 0b
echo =========================================================================
echo    STUDENT ATTENDANCE ANALYZER USING SET THEORY
echo    College Engineering Project - Sandip University Portal
echo =========================================================================
echo.
echo [*] Starting Flask Backend Server on http://localhost:5000 ...
cd /d "%~dp0backend"

:: Launch browser in 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Start the Flask web application
python app.py

pause
