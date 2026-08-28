@echo off
REM Build VesperManifest.exe. Run this ON WINDOWS - PyInstaller cannot
REM cross-compile, so a Mac cannot produce a .exe no matter what you pass it.
REM
REM Needs Python 3.10+ from python.org, "Add python.exe to PATH" ticked.

setlocal
cd /d "%~dp0"

echo === installing dependencies ===
py -m pip install --upgrade pip
py -m pip install -r requirements.txt || goto :failed

echo.
echo === generating the icon ===
py rpg\make_icon.py || goto :failed

echo.
echo === building ===
py -m PyInstaller --noconfirm --clean VesperManifest.spec || goto :failed

echo.
echo === checking the build actually runs ===
dist\VesperManifest\VesperManifest.exe --selftest || goto :failed

echo.
echo ============================================================
echo  Done.  dist\VesperManifest\VesperManifest.exe
echo  Ship the whole dist\VesperManifest folder, not just the exe.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo BUILD FAILED - see the error above.
pause
exit /b 1

