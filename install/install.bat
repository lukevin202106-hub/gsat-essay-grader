@echo off
rem gsat-essay-grader installer for Windows: runs install.ps1 next to this file.
rem This file stays ASCII-only so cmd.exe reads it correctly on any code page.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 pause
