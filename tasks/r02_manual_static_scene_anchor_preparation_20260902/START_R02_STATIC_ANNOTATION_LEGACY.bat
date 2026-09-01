@echo off
setlocal
cd /d "%~dp0"
"D:\MINICONDA\envs\py311\python.exe" "%~dp0r02_static_scene_annotator.py"
if errorlevel 1 pause
endlocal
