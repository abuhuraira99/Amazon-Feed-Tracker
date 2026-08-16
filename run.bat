@echo off
echo Starting Amazon Feed Update Server...
call venv\Scripts\activate.bat
start http://127.0.0.1:5000
python app.py
pause
