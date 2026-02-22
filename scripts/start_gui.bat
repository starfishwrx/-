@echo off
setlocal
set ROOT_DIR=%~dp0..
set PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" "%ROOT_DIR%\report_launcher_gui.py"
) else (
  python "%ROOT_DIR%\report_launcher_gui.py"
)
