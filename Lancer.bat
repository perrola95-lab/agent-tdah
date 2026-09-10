@echo off
chcp 65001 > nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title Agent d'Apprentissage Adaptatif - TDAH (4eme)

echo ========================================================
echo   Démarrage de l'Agent d'Apprentissage Adaptatif (4ème)
echo ========================================================
echo.

:: 1. Vérification de Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'a pas été détecté sur votre système.
    echo.
    echo Pour installer Python en 2 minutes :
    echo 1. Téléchargez Python (3.11 ou 3.12 recommandé) sur : https://www.python.org/downloads/
    echo 2. PENDANT L'INSTALLATION : Cochez impérativement la case "Add Python to PATH" !
    echo 3. Redémarrez ce script (Lancer.bat).
    echo.
    pause
    exit /b 1
)

:: 2. Vérification / Réparation du venv
set RECREATE_VENV=0
if not exist "venv\Scripts\python.exe" (
    set RECREATE_VENV=1
) else (
    venv\Scripts\python.exe -c "import sys" >nul 2>nul
    if %errorlevel% neq 0 (
        set RECREATE_VENV=1
    )
)

if %RECREATE_VENV%==1 (
    echo Configuration de l'environnement virtuel local...
    if exist "venv" rmdir /s /q venv
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERREUR] Échec de la création de l'environnement virtuel.
        pause
        exit /b 1
    )
    echo Installation des bibliothèques requises...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: 3. Vérification du fichier .env
if not exist ".env" (
    echo [ATTENTION] Aucun fichier .env détecté.
    echo N'oubliez pas d'indiquer votre GEMINI_API_KEY dans le fichier .env.
    echo.
)

:: 4. Lancement de Streamlit
echo.
echo Lancement de l'application...
echo L'interface va s'ouvrir automatiquement dans votre navigateur !
echo.
"%~dp0venv\Scripts\python.exe" -m streamlit run app.py

pause
