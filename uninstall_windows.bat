@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_NAME=Launchpad_X_performance"
set "DEFAULT_LIBRARY=%USERPROFILE%\Documents\Ableton\User Library"

echo.
echo Launchpad X Performance uninstaller for Windows
echo ================================================
echo.

echo Select Ableton User Library:
echo.
echo 1^) Standard location:
echo    "%DEFAULT_LIBRARY%"
echo.
echo 2^) Enter another User Library path
echo.

set /p "CHOICE=Enter 1 or 2 [1]: "
if not defined CHOICE set "CHOICE=1"

if "%CHOICE%"=="1" (
    set "USER_LIBRARY=%DEFAULT_LIBRARY%"
) else if "%CHOICE%"=="2" (
    echo.
    set /p "USER_LIBRARY=Enter the full path to Ableton User Library: "
) else (
    echo.
    echo ERROR: Enter 1 or 2.
    pause
    exit /b 1
)

if not defined USER_LIBRARY (
    echo.
    echo ERROR: User Library path is empty.
    pause
    exit /b 1
)

set "DESTINATION=%USER_LIBRARY%\Remote Scripts\%SCRIPT_NAME%"

echo.
echo Removing:
echo "%DESTINATION%"
echo.

if not exist "%DESTINATION%\" (
    echo Launchpad X Performance is not installed there.
    pause
    exit /b 0
)

rmdir /s /q "%DESTINATION%"

if exist "%DESTINATION%\" (
    echo ERROR: Could not remove the script.
    echo Close Ableton Live and try again.
    pause
    exit /b 1
)

echo.
echo Uninstallation complete.
echo Restart Ableton Live.
echo.
pause
exit /b 0