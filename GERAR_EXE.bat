@echo off
title Gerando Executavel - Creditall Bot PN
color 0A
echo.
echo  =========================================
echo   CREDITALL BOT PN - Gerador de EXE
echo  =========================================
echo.

echo [1/4] Instalando PyInstaller e dependencias...
pip install pyinstaller pillow customtkinter pandas openpyxl selenium
echo.

echo [2/4] Criando pasta data se nao existir...
if not exist "data" mkdir "data"
echo.

echo [3/4] Gerando executavel...
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "CreditallBot_PN" ^
  --add-data "logo_creditall.png;." ^
  --add-data "bot_core_gemini_PN.py;." ^
  --hidden-import customtkinter ^
  --hidden-import PIL ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageTk ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  --hidden-import selenium ^
  --hidden-import selenium.webdriver ^
  --hidden-import selenium.webdriver.chrome.service ^
  --hidden-import selenium.webdriver.chrome.options ^
  --hidden-import selenium.webdriver.support.ui ^
  --hidden-import selenium.webdriver.support.expected_conditions ^
  --hidden-import selenium.webdriver.common.by ^
  --hidden-import selenium.webdriver.common.keys ^
  --collect-all customtkinter ^
  --collect-all PIL ^
  main_gemini_PN.py

echo.
echo [4/4] Verificando resultado...
if exist "dist\CreditallBot_PN.exe" (
    color 0A
    echo  =========================================
    echo   SUCESSO! Executavel gerado em:
    echo   dist\CreditallBot_PN.exe
    echo  =========================================
) else (
    color 0C
    echo  =========================================
    echo   ERRO! Executavel nao foi gerado.
    echo   Leia o log acima para ver o problema.
    echo  =========================================
)
echo.
pause
