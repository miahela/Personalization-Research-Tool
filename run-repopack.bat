@echo off
REM Delete repopack-output.txt if it exists
if exist repopack-output.txt del repopack-output.txt

REM Run repopack command
repopack --style=xml

REM Pause to keep the window open and show any output
pause