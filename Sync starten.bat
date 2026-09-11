@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   StevePrints - Etsy-Sync
echo   ------------------------
echo.
python etsy_sync.py
if errorlevel 1 (
  echo.
  echo   Es ist etwas schiefgegangen. Meldung oben durchlesen.
) else (
  echo.
  echo   Fertig. steveprints.html ist aktuell.
)
echo.
pause
