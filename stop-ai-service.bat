@echo off
echo Stopping AI Services...

taskkill /FI "WindowTitle eq Neo Framework*" /F > nul 2>&1
taskkill /FI "WindowTitle eq AI Service*" /F > nul 2>&1

echo Services stopped.
echo.