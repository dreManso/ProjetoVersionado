@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Controle de Cozinha
python -c "import fastapi, sqlalchemy" 2>NUL || (
  echo Instalando o programa pela primeira vez...
  python -m pip install -r requirements.txt
)
python run.py
pause
