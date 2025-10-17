@echo off
REM FileHarbor Test Runner for Windows

setlocal

if "%1"=="" (
    echo Running all tests...
    python run_tests.py
) else if "%1"=="integration" (
    echo Running integration tests...
    python run_tests.py integration
) else if "%1"=="security" (
    echo Running security tests...
    python run_tests.py security
) else if "%1"=="e2e" (
    echo Running end-to-end tests...
    python run_tests.py e2e
) else if "%1"=="common" (
    echo Running common tests...
    python run_tests.py common
) else if "%1"=="coverage" (
    echo Running tests with coverage...
    pytest --cov=fileharbor --cov-report=html --cov-report=term
    echo.
    echo Coverage report generated: htmlcov\index.html
) else if "%1"=="help" (
    echo FileHarbor Test Runner
    echo.
    echo Usage: test.bat [option]
    echo.
    echo Options:
    echo   (none)       Run all tests
    echo   integration  Run integration tests only
    echo   security     Run security tests only
    echo   e2e          Run end-to-end tests only
    echo   common       Run common/unit tests only
    echo   coverage     Run all tests with coverage report
    echo   help         Show this help message
) else (
    echo Unknown option: %1
    echo Run 'test.bat help' for usage information
    exit /b 1
)

endlocal
