@echo off
REM Opens the 372-A Tech Arena dashboard with autoplay-with-sound enabled.
REM (Regular double-clicking index.html won't autoplay music -- browsers
REM  block audio autoplay by default. This flag tells the browser it's OK.)

set DASHBOARD=%~dp0index.html
set CHROME="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set EDGE="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
set PROFILE=%LOCALAPPDATA%\372ADashboardAutoplayProfile

REM NOTE: if Chrome/Edge is already running, launching with flags alone
REM gets ignored -- the URL just gets handed to the existing window over
REM IPC. A separate --user-data-dir forces a genuinely new browser
REM process so the autoplay flag actually takes effect.

if exist %CHROME% (
    start "" %CHROME% --user-data-dir="%PROFILE%" --autoplay-policy=no-user-gesture-required --new-window "%DASHBOARD%"
) else if exist %EDGE% (
    start "" %EDGE% --user-data-dir="%PROFILE%" --autoplay-policy=no-user-gesture-required --new-window "%DASHBOARD%"
) else (
    echo Could not find Chrome or Edge in their default install paths.
    echo Opening normally instead -- you'll need to click SOUND once.
    start "" "%DASHBOARD%"
)
