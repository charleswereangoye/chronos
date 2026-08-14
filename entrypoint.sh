#!/bin/bash
echo "Checking for dependency updates..."
pip uninstall -y twikit
pip install --default-timeout=1000 --upgrade -r requirements.txt
echo "Starting Telegram Orchestrator..."
exec python orchestrator/telegram_orchestrator.py
