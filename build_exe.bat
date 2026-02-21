@echo off
setlocal

if not defined VIRTUAL_ENV (
    echo Activating virtual environment .venv...
    call .venv\Scripts\activate
)

echo Ensuring pyinstaller is available...
python -m pip install --upgrade pyinstaller >nul

echo Building executable...
pyinstaller --clean build_exe.spec

echo Build finished. Executable is in dist\generate_daily_report.exe

endlocal
