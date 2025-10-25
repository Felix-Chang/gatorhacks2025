@echo off
echo Starting NYC CO2 Advanced Backend Server...
echo.

cd backend

echo Installing/updating dependencies...
python -m pip install -r requirements.txt

echo.
echo Starting Advanced NYC CO2 Simulation API...
echo.

python main_advanced.py

pause
