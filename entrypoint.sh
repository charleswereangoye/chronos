#!/bin/bash
if [ "$UPGRADE_DEPS" = "true" ]; then
    echo "Checking for dependency updates..."
    pip uninstall -y twikit 2>/dev/null || true
    pip install --default-timeout=100 --upgrade -r requirements.txt
fi
echo "Starting Telegram Orchestrator..."
exec python orchestrator/telegram_orchestrator.py
