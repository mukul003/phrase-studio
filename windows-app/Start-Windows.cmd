@echo off
setlocal
cd /d "%~dp0"
where dotnet >nul 2>nul
if errorlevel 1 (
 echo Install the .NET 8 SDK from https://dotnet.microsoft.com/download/dotnet/8.0 and run this again.
 pause
 exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
 echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/ with the Python launcher.
 pause
 exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
 echo Install FFmpeg and add its bin folder to PATH. ffmpeg and ffprobe are both required.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r engine\requirements.txt
if errorlevel 1 (
 pause
 exit /b 1
)
set "PHRASE_PYTHON=%CD%\.venv\Scripts\python.exe"
set "PHRASE_OPEN_BROWSER=1"
dotnet run --project PhraseStudio.csproj --no-launch-profile
pause
