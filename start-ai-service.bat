@echo off
echo Starting Neo AI Service...
echo.

:: First check if ports are available
echo Checking if ports are available...
netstat -ano | findstr :9999 >nul
if %errorlevel% == 0 (
    echo ERROR: Port 9999 is already in use!
    echo Please run stop-all-services.bat first to clean up.
    pause
    exit /b 1
)

netstat -ano | findstr :8080 >nul
if %errorlevel% == 0 (
    echo ERROR: Port 8080 is already in use!
    echo Please run stop-all-services.bat first to clean up.
    pause
    exit /b 1
)

echo Ports are available. Starting services...
echo.

:: Start Neo Framework
echo Starting Neo Framework...
start "Neo Framework" neo-framework.exe

:: Wait for Framework to start
echo Waiting for Neo Framework to start...
timeout /t 5 /nobreak >nul

:: Check if Framework started successfully
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Neo Framework failed to start!
    echo Check the Neo Framework window for error messages.
    pause
    exit /b 1
)

echo Neo Framework started successfully!
echo.

:: Start AI Service
echo Starting AI Service...
cd neo-ai-service
start "AI Service" python src\main.py
cd ..

:: Wait for AI Service to start
echo Waiting for AI Service to start...
timeout /t 5 /nobreak >nul

:: Check if AI Service started successfully
curl -s http://localhost:8080/api/ai-service/health >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: AI Service health check failed.
    echo The service might still be starting up...
)

echo.
echo ========================================
echo Services started!
echo ========================================
echo.
echo Neo Framework: http://localhost:8080
echo Health Check: http://localhost:8080/health
echo AI Service Health: http://localhost:8080/api/ai-service/health
echo.
echo Test commands:
echo.
echo 1. Test Ollama (local):
echo    curl -X POST http://localhost:8080/api/ai-service/chat -H "Content-Type: application/json" -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}], \"model\": \"gemma3:12b\"}"
echo.
echo 2. Test OpenRouter (cloud):
echo    curl -X POST http://localhost:8080/api/ai-service/chat -H "Content-Type: application/json" -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}], \"model\": \"cognitivecomputations/dolphin-mistral-24b-venice-edition:free\"}"
echo.
pause