@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Zainstaluj Python 3 ze strony https://www.python.org/downloads/windows/
  echo Zaznacz opcje instalacji Python Launcher oraz tkinter.
  pause
  exit /b 1
)
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Instalacja nie powiodla sie. Sprawdz polaczenie z internetem.
  pause
  exit /b 1
)
set "ORBIT_HOME=%~dp0"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Orbit.lnk'); $s.TargetPath=$env:ORBIT_HOME+'uruchom.bat'; $s.WorkingDirectory=$env:ORBIT_HOME; $s.Save()"
echo Gotowe. Uzyj skrotu Orbit na pulpicie lub pliku uruchom.bat.
pause