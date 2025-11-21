#!/bin/bash
# /usr/local/bin/auto-shutdown.sh
# Auto shutdown + desligar monitor por inatividade
set -euo pipefail

# --- CONFIGURAÇÕES (segundos) ---
LIMITE=600        # tempo de inatividade para desligar o PC (s)
TELA_LIMITE=2    # tempo de inatividade para desligar a tela (s)
INTERVALO=5       # intervalo do loop (s)

logger_prefix="auto-shutdown"

# encontra usuário da sessão X/Wayland ativa e DISPLAY/XAUTHORITY
find_active_session() {
    USERNAME=$(who | awk '$2 ~ /^:/{print $1; exit}' || true)

    if [[ -z "$USERNAME" ]]; then
        USERNAME=$(ps -eo user:20,comm | awk '/Xorg|Xwayland/ {print $1; exit}' || true)
    fi

    if [[ -z "$USERNAME" ]]; then
        for d in /home/*; do
            [[ -f "$d/.Xauthority" ]] && USERNAME=$(basename "$d") && break
        done
    fi

    if [[ -z "${USERNAME:-}" ]]; then
        logger -t "$logger_prefix" "Nenhum usuário de sessão gráfica encontrado."
        return 1
    fi

    DISPLAY_VAL=":0"
    XAUTH="/home/${USERNAME}/.Xauthority"
    
    echo "$USERNAME" "$DISPLAY_VAL" "$XAUTH"
    return 0
}

find_gpu_busy_file() {
    for f in /sys/class/drm/card*/device/gpu_busy_percent; do
        [[ -f "$f" ]] && { echo "$f"; return 0; }
    done
    return 1
}

gpu_idle() {
    local gpufile="$1"
    if [[ -n "$gpufile" ]] && [[ -f "$gpufile" ]]; then
        read -r uso < "$gpufile" 2>/dev/null || uso=""
        if [[ "$uso" =~ ^[0-9]+$ ]] && (( uso <= 10 )); then
            return 0
        fi
        return 1
    fi
    return 0
}

desligar_monitor() {
    local user="$1"
    local display="$2"
    local xauth="$3"

    export DISPLAY="$display"
    export XAUTHORITY="$xauth"

    # Comandos executados diretamente sem sudo para evitar pedido de senha
    gsettings set org.cinnamon.desktop.screensaver lock-enabled false 2>/dev/null || true
    gsettings set org.cinnamon.desktop.screensaver idle-activation-enabled false 2>/dev/null || true
    gsettings set org.cinnamon.settings-daemon.plugins.power lock-on-suspend false 2>/dev/null || true
    gsettings set org.cinnamon.settings-daemon.plugins.power lock-on-lid-close false 2>/dev/null || true
    gsettings set org.cinnamon.settings-daemon.plugins.power lock-on-sleep false 2>/dev/null || true
    
    # Tenta também para GNOME caso mude o ambiente
    gsettings set org.gnome.desktop.screensaver lock-enabled false 2>/dev/null || true
    gsettings set org.gnome.desktop.lockdown disable-lock-screen true 2>/dev/null || true

    xset +dpms 2>/dev/null || true
    xset dpms force off 2>/dev/null || true

    logger -t "$logger_prefix" "Monitor: comando xset dpms force off enviado."
}

get_idle_seconds() {
    local display="$1"
    local xauth="$2"
    export DISPLAY="$display"
    export XAUTHORITY="$xauth"

    if ! command -v xprintidle >/dev/null 2>&1; then
        echo "ERR_NO_XPRINTIDLE"
        return 0
    fi

    local idle_ms
    idle_ms=$(xprintidle 2>/dev/null || echo 0)

    if [[ "$idle_ms" =~ ^[0-9]+$ ]]; then
        echo $((idle_ms / 1000))
    else
        echo 0
    fi
}

read -r ACTIVE_USER DISPLAY XAUTH <<< "$(find_active_session)" || exit 1
GPU_FILE=$(find_gpu_busy_file || true)

logger -t "$logger_prefix" "Iniciado por $ACTIVE_USER. LIMITE=${LIMITE}s TELA_LIMITE=${TELA_LIMITE}s"

TIMER_PC=0
TIMER_TELA=0

while true; do
    IDLE_SEC=$(get_idle_seconds "$DISPLAY" "$XAUTH")

    if [[ "$IDLE_SEC" == "ERR_NO_XPRINTIDLE" ]]; then
        logger -t "$logger_prefix" "xprintidle faltando."
        exit 1
    fi

    if (( IDLE_SEC >= TELA_LIMITE )); then
        TIMER_TELA=$((TIMER_TELA + INTERVALO))
    else
        TIMER_TELA=0
    fi

    if (( TIMER_TELA >= TELA_LIMITE )); then
        desligar_monitor "$ACTIVE_USER" "$DISPLAY" "$XAUTH"
        TIMER_TELA=0
    fi

    if gpu_idle "$GPU_FILE"; then
        GPU_OCIOSA=0
    else
        GPU_OCIOSA=1
    fi

    if (( IDLE_SEC >= LIMITE )) && (( GPU_OCIOSA == 0 )); then
        TIMER_PC=$((TIMER_PC + INTERVALO))
    else
        TIMER_PC=0
    fi

    if (( TIMER_PC >= LIMITE )); then
        logger -t "$logger_prefix" "Solicitando poweroff."
        # Tenta desligar via systemctl diretamente sem sudo
        systemctl poweroff || {
            # Fallback se falhar tenta via dbus
            dbus-send --system --print-reply --dest=org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager.PowerOff boolean:true
        }
        TIMER_PC=0
    fi

    sleep "$INTERVALO"
done
