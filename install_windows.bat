@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_NAME=Launchpad_X_performance"
set "PROJECT_DIR=%~dp0"
set "SOURCE_DIR=%PROJECT_DIR%src\%SCRIPT_NAME%"
set "DEFAULT_LIBRARY=%USERPROFILE%\Documents\Ableton\User Library"

echo.
echo Launchpad X Performance installer for Windows
echo ==============================================
echo.

if not exist "%SOURCE_DIR%\" (
    echo ERROR: Source folder was not found:
    echo "%SOURCE_DIR%"
    echo.
    pause
    exit /b 1
)

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

set "REMOTE_SCRIPTS=%USER_LIBRARY%\Remote Scripts"
set "DESTINATION=%REMOTE_SCRIPTS%\%SCRIPT_NAME%"

echo.
echo Source:
echo "%SOURCE_DIR%"
echo.
echo Destination:
echo "%DESTINATION%"
echo.

if not exist "%REMOTE_SCRIPTS%\" (
    mkdir "%REMOTE_SCRIPTS%"
    if errorlevel 1 (
        echo ERROR: Could not create:
        echo "%REMOTE_SCRIPTS%"
        pause
        exit /b 1
    )
)

if exist "%DESTINATION%\" (
    echo Removing previous installation...
    rmdir /s /q "%DESTINATION%"

    if exist "%DESTINATION%\" (
        echo ERROR: Could not remove the previous installation.
        echo Close Ableton Live and try again.
        pause
        exit /b 1
    )
)

echo Installing...
xcopy "%SOURCE_DIR%" "%DESTINATION%\" /E /I /H /Y /Q >nul

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed.
    pause
    exit /b 1
)

echo.
echo Installation complete.
echo.
echo Restart Ableton Live, then select:
echo Launchpad_X_performance
echo in Settings ^> Link, Tempo ^& MIDI.
echo.
pause
exit /b 0