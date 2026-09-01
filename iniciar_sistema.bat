@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

title Pokémon Champions - Sistema Local
cls
echo ==========================================
echo   Pokémon Champions - Sistema Local
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado.
    echo Instale o Python e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

if not exist "app.py" (
    echo ERRO: app.py nao encontrado nesta pasta.
    echo Pasta atual: %CD%
    echo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERRO: requirements.txt nao encontrado nesta pasta.
    echo.
    pause
    exit /b 1
)

echo Verificando dependencias...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERRO: Nao foi possivel instalar as dependencias.
        echo Verifique sua conexao com a internet e tente novamente.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Iniciando o sistema...
echo Se o navegador nao abrir sozinho, acesse:
echo http://127.0.0.1:5000
echo.
echo Para encerrar o sistema, feche esta janela ou pressione CTRL+C.
echo.

python app.py

echo.
echo O sistema foi encerrado.
pause
