@echo off
title Gerar EXE - Creditall Bot PN
color 0A
echo.
echo  =========================================
echo   CREDITALL BOT PN - Gerador de EXE
echo  =========================================
echo.

C:\Users\David\AppData\Local\Programs\Python\Python313\python.exe -m PyInstaller ^
  --noconfirm --clean --onefile --windowed ^
  --name "CreditallBot_PN" ^
  --add-data "logo_creditall.png;." ^
  --add-data "bot_core_gemini_PN.py;." ^
  --add-data "updater.py;." ^
  --hidden-import customtkinter ^
  --hidden-import PIL ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  --hidden-import selenium ^
  --hidden-import selenium_stealth ^
  --hidden-import urllib.request ^
  --collect-all customtkinter ^
  --collect-all PIL ^
  --collect-all selenium_stealth ^
  main_gemini_PN.py

echo.
if exist "dist\CreditallBot_PN.exe" (
    color 0A
    echo  =========================================
    echo   SUCESSO! EXE gerado em: dist\CreditallBot_PN.exe
    echo  =========================================
) else (
    color 0C
    echo  =========================================
    echo   ERRO! Veja o log acima.
    echo  =========================================
)
echo.
pause
