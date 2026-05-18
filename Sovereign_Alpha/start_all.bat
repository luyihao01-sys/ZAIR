@echo off
REM start_all.bat - 一键启动 ZAIR 本地演示（Windows）
REM 说明：此脚本会在单独的 PowerShell 窗口中启动 Ollama（如果已安装）、Validator、Miner，并运行集成测试。

set ROOT_DIR=%~dp0
echo Root directory: %ROOT_DIR%














exit /B 0pause > nulecho Press any key to exit this launcher...echo If any venv was created, the first run may install dependencies and take a few minutes.
necho Launched Ollama (optional), Validator, Miner, and Test windows.start "Test" powershell -NoExit -Command "Set-Location '%ROOT_DIR%'; Write-Host 'Running integration test...'; python test_integration.py; Write-Host 'Integration test finished.'; Pause"
:: 4) Integration Test (runs in its own window)start "Miner" powershell -NoExit -Command "Set-Location '%ROOT_DIR%zair-miner'; if (-Not (Test-Path 'venv')) { Write-Host 'Creating venv and installing miner deps...'; python -m venv venv; & .\venv\Scripts\Activate; pip install -r requirements.txt } else { & .\venv\Scripts\Activate }; Write-Host 'Ensure .env exists and ETHEREUM_PRIVATE_KEY is set.'; Write-Host 'Starting Miner...'; python src/miner.py --node-name MyNode --region MEA"
:: 3) Minerstart "Validator" powershell -NoExit -Command "Set-Location '%ROOT_DIR%zair-validator'; if (-Not (Test-Path 'venv')) { Write-Host 'Creating venv and installing validator deps...'; python -m venv venv; & .\venv\Scripts\Activate; pip install -r requirements.txt } else { & .\venv\Scripts\Activate }; Write-Host 'Starting Validator (uvicorn) on :8001...'; python -m uvicorn src.api:app --reload --port 8001"
:: 2) Validator APIstart "Ollama" powershell -NoExit -Command "Set-Location '%ROOT_DIR%'; if (Get-Command ollama -ErrorAction SilentlyContinue) { Write-Host 'Starting Ollama...'; ollama serve } else { Write-Host 'ollama 未安装或不在 PATH。请按说明安装：https://ollama.ai'; Pause }":: 1) Ollama (可选)