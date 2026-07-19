$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting EduInsight backend and frontend..." -ForegroundColor Cyan

Start-Process powershell.exe -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$projectRoot\backend'; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000"
)

Start-Process powershell.exe -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$projectRoot\frontend'; npm install; npm run dev"
)

Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Green
