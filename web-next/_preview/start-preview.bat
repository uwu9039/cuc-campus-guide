@echo off
setlocal
rem 前端预览：后端不运行也能看页面。仓库根目录下双击即可。
cd /d "%~dp0..\.."

if not exist "web-next\_preview\fixtures\items.json" (
  echo [1/2] 生成前端样张 fixtures...
  ".venv\Scripts\python.exe" web-next\_preview\build_fixtures.py
)

echo [2/2] 启动预览服务   http://127.0.0.1:8010/field
echo       ^(后端 app.py / uvicorn 不启动；关掉这个窗口即停止^)
start "" "http://127.0.0.1:8010/field"
".venv\Scripts\python.exe" web-next\_preview\mock_server.py --port 8010
