@echo off
cd /d "%~dp0"
echo ====================================================
echo Starting V2V Voice-to-Voice Dashboard...
echo ====================================================
.\venv\Scripts\python.exe -m streamlit run app.py
pause
