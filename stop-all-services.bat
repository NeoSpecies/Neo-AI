@echo off
echo Stopping all Neo services...

echo.
echo Stopping Python processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel% == 0 (
    echo Python processes stopped.
) else (
    echo No Python processes found.
)

echo.
echo Stopping Neo Framework...
taskkill /F /IM neo-framework.exe 2>nul
if %errorlevel% == 0 (
    echo Neo Framework stopped.
) else (
    echo No Neo Framework process found.
)

echo.
echo Checking port 9999...
netstat -ano | findstr :9999
if %errorlevel% == 0 (
    echo Port 9999 is still in use. Trying to find and kill the process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9999') do (
        echo Killing process PID: %%a
        taskkill /F /PID %%a 2>nul
    )
) else (
    echo Port 9999 is free.
)

echo.
echo Checking port 8080...
netstat -ano | findstr :8080
if %errorlevel% == 0 (
    echo Port 8080 is still in use. Trying to find and kill the process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080') do (
        echo Killing process PID: %%a
        taskkill /F /PID %%a 2>nul
    )
) else (
    echo Port 8080 is free.
)

echo.
echo All services stopped.
echo You can now start fresh with start-ai-service.bat
pause