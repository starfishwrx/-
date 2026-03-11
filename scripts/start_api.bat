@echo off
setlocal
set ROOT_DIR=%~dp0..
set UVICORN_EXE=%ROOT_DIR%\.venv\Scripts\uvicorn.exe
set PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe

if exist "%UVICORN_EXE%" (
  "%UVICORN_EXE%" fastapi_app:app --host 0.0.0.0 --port 8000
  goto :eof
)

if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" -m uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
  goto :eof
)

uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
