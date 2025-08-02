@echo off
echo Starting Neo Framework...
echo.

REM 检查是否存在可执行文件
if not exist neo-framework.exe (
    echo Error: neo-framework.exe not found!
    echo Please ensure the executable is in the current directory.
    pause
    exit /b 1
)

REM 启动Neo Framework
echo Neo Framework is starting on port 9999...
echo Press Ctrl+C to stop.
echo.

neo-framework.exe -port 9999

pause