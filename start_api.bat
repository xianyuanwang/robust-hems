@echo off
REM HEMS API Server Startup Script for Windows

echo ==========================================
echo   HEMS AI Scheduling API Server
echo ==========================================
echo.

REM Check if required packages are installed
python -c "import fastapi, uvicorn, ortools" 2>nul
if errorlevel 1 (
    echo Error: Required packages not found.
    echo Please install dependencies:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo [OK] Dependencies OK
echo.

REM Configuration
set HOST=%HEMS_HOST:0.0.0.0%
set PORT=%HEMS_PORT:8000%
set WORKERS=%HEMS_WORKERS:4%
set LOG_LEVEL=%HEMS_LOG_LEVEL:info%

echo Starting API server...
echo   Host: %HOST%
echo   Port: %PORT%
echo   Workers: %WORKERS%
echo   Log Level: %LOG_LEVEL%
echo.
echo API Documentation will be available at:
echo   Swagger UI: http://localhost:%PORT%/docs
echo   ReDoc:      http://localhost:%PORT%/redoc
echo.
echo Press Ctrl+C to stop the server
echo ==========================================
echo.

REM Start the server
cd src
uvicorn api_server:app --host %HOST% --port %PORT% --workers %WORKERS% --log-level %LOG_LEVEL%
