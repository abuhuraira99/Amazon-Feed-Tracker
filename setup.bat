@echo off
echo Setting up Amazon Feed Update Project environment...
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo Setup complete! Run run.bat to start the server.
pause
