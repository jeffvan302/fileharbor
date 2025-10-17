@echo off
REM FileHarbor Windows Setup Script
REM Sets up development environment on Windows with Miniconda

echo ============================================================
echo   FileHarbor Windows Setup
echo ============================================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found in PATH
    echo.
    echo Please install Miniconda from:
    echo https://docs.conda.io/en/latest/miniconda.html
    echo.
    echo After installation, restart your terminal and run this script again.
    pause
    exit /b 1
)

echo Found conda installation
echo.

REM Check if environment already exists
conda env list | findstr /C:"fileharbor" >nul
if %ERRORLEVEL% EQU 0 (
    echo Environment 'fileharbor' already exists.
    choice /C YN /M "Do you want to remove it and create a fresh environment"
    if errorlevel 2 goto :skip_create
    echo Removing existing environment...
    call conda env remove -n fileharbor -y
)

echo Creating conda environment from environment.yml...
call conda env create -f environment.yml
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create conda environment
    pause
    exit /b 1
)

:skip_create
echo.
echo Activating environment...
call conda activate fileharbor
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate environment
    echo Try running: conda activate fileharbor
    pause
    exit /b 1
)

echo.
echo Installing FileHarbor in development mode...
pip install -e .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install FileHarbor
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Environment 'fileharbor' is ready to use.
echo.
echo To activate the environment, run:
echo   conda activate fileharbor
echo.
echo To start developing:
echo   1. Open this folder in VS Code
echo   2. Select the Python interpreter (Ctrl+Shift+P -^> Python: Select Interpreter)
echo   3. Choose the 'fileharbor' conda environment
echo.
echo Available commands:
echo   fileharbor-server server_config.json  - Start server
echo   fileharbor-config server_config.json  - Configure server
echo   python run_tests.py                   - Run tests
echo.
echo ============================================================
echo.

pause
