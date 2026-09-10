@echo off
chcp 65001 > nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
echo Installation des dépendances pour l'Agent d'Apprentissage TDAH...
if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat
pip install -r requirements.txt
echo Installation terminée !
pause

