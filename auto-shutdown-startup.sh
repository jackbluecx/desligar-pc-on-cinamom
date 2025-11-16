#!/bin/bash
# Script para aplicar Auto-Desligamento e DPMS na inicialização

CONFIG_FILE="$HOME/.auto_shutdown_config.json"

# Verifica se o arquivo de configuração existe
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuração não encontrada: $CONFIG_FILE"
    exit 1
fi

# Lê configurações do JSON usando jq
SHUTDOWN_ACTIVE=$(jq -r '.shutdown_active' "$CONFIG_FILE")
SHUTDOWN_TIME=$(jq -r '.shutdown_time' "$CONFIG_FILE")
SCREEN_ACTIVE=$(jq -r '.screen_active' "$CONFIG_FILE")
SCREEN_TIME=$(jq -r '.screen_off_time' "$CONFIG_FILE")

# Mata instâncias antigas para evitar conflito
pkill -x xautolock 2>/dev/null

# Auto-desligamento com xautolock
if [ "$SHUTDOWN_ACTIVE" = "true" ]; then
    xautolock -time "$SHUTDOWN_TIME" -locker /bin/true \
              -killer "systemctl poweroff" -killtime 0 \
              -notify 60 \
              -notifier "notify-send 'Desligando em 1 minuto por inatividade...'" &
fi

# DPMS (desligamento de tela)
if [ "$SCREEN_ACTIVE" = "true" ]; then
    SECONDS=$((SCREEN_TIME*60))
    xset +dpms
    xset dpms "$SECONDS" "$SECONDS" "$SECONDS"
fi
