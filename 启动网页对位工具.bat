@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo 正在安装网页程序依赖，请稍候...
    "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements-web.txt"
)
start "无畏契约对位工具" "%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0web_app.py"
