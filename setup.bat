@echo off
title Real Estate Scraper Setup
mode con: cols=80 lines=30
color 0A

echo ==================================================================
echo                    Real Estate Scraper Installer
echo ==================================================================
echo.
echo Welcome to the Real Estate Scraper installer!
echo.
echo This installer will set up the Real Estate Scraper application on your
echo computer and create shortcuts for easy access.
echo.
echo You have two installation options:
echo.
echo 1. Quick Install (Recommended)
echo    - Creates shortcuts to run the application with Python
echo    - Faster installation
echo    - Requires Python to be installed
echo.
echo 2. Full Installation with Executable
echo    - Creates a standalone executable
echo    - Longer installation time
echo    - Creates desktop shortcut to the executable
echo    - Still requires Python for the initial build process
echo.
echo ==================================================================
echo.

:CHOICE
SET /P CHOICE="Enter your choice (1 or 2): "
IF "%CHOICE%"=="1" GOTO QUICK
IF "%CHOICE%"=="2" GOTO FULL
echo Invalid choice. Please enter 1 or 2.
GOTO CHOICE

:QUICK
cls
echo ==================================================================
echo                   Quick Installation Selected
echo ==================================================================
echo.
echo Running the installer script...
echo.
call installer.bat
GOTO END

:FULL
cls
echo ==================================================================
echo                  Full Installation Selected
echo ==================================================================
echo.
echo This process will:
echo 1. Install necessary Python packages
echo 2. Create an executable version of the application
echo 3. Create shortcuts on your desktop
echo.
echo This may take several minutes to complete.
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.9 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller
echo.

REM Run the executable creator script
echo Setting up executable creation...
python create_executable.py
echo.

REM Run the build script
echo Building executable...
call build_exe.bat
echo.

echo Installation completed!
GOTO END

:END
echo.
echo ==================================================================
echo                  Installation Complete!
echo ==================================================================
echo.
echo Thank you for installing Real Estate Scraper!
echo.
pause