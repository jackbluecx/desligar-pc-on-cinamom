#!/usr/bin/env python3
import gi
import subprocess
import os
import json
import sys
from subprocess import DEVNULL

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# ---------------------------
# Lockfile — evita múltiplas instâncias
# ---------------------------
LOCKFILE = os.path.expanduser("~/.auto_shutdown_gui.lock")

def lockfile_is_running(path):
    try:
        with open(path, "r") as f:
            pid = int(f.read().strip())
        # verifica se o PID ainda existe
        os.kill(pid, 0)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        # PID inválido ou processo não existe
        return False

# Se existe e o PID está vivo -> sair
if lockfile_is_running(LOCKFILE):
    print("Outra instância já está rodando. Saindo.")
    sys.exit(0)

# Se existe mas inválido/stale, remove e continua
if os.path.exists(LOCKFILE):
    try:
        os.remove(LOCKFILE)
    except Exception:
        pass

# cria lockfile atual
with open(LOCKFILE, "w") as f:
    f.write(str(os.getpid()))

def remove_lockfile():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
    except Exception:
        pass

# ---------------------------
# Configuração (arquivo JSON)
# ---------------------------
CONFIG_FILE = os.path.expanduser("~/.auto_shutdown_config.json")
default_config = {
    "shutdown_time": 30,
    "shutdown_active": False,
    "screen_off_time": 10,
    "screen_active": False
}

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except Exception:
        config = default_config.copy()
else:
    config = default_config.copy()

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except Exception as e:
        subprocess.Popen(["notify-send", "Auto-Desligamento", f"Erro ao salvar config: {e}"])

# ---------------------------
# Helpers para xautolock / DPMS
# ---------------------------
def is_xautolock_running():
    return subprocess.call(["pgrep", "-x", "xautolock"], stdout=DEVNULL, stderr=DEVNULL) == 0

def start_xautolock(minutes):
    try:
        subprocess.Popen([
            "xautolock",
            "-time", str(minutes),
            "-locker", "systemctl poweroff",
            "-notify", "60",
            "-notifier", "notify-send 'Desligando em 1 minuto por inatividade...'"
        ], stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)
    except Exception:
        pass

def stop_xautolock():
    try:
        subprocess.call(["pkill", "-x", "xautolock"], stdout=DEVNULL, stderr=DEVNULL)
    except Exception:
        pass

def is_dpms_enabled():
    try:
        out = subprocess.check_output(["xset", "q"], stderr=DEVNULL).decode(errors="ignore")
        return "DPMS is Enabled" in out
    except Exception:
        return False

def enable_dpms(minutes):
    try:
        seconds = int(minutes) * 60
        subprocess.call(["xset", "+dpms"], stdout=DEVNULL, stderr=DEVNULL)
        subprocess.call(["xset", "dpms", str(seconds), str(seconds), str(seconds)], stdout=DEVNULL, stderr=DEVNULL)
    except Exception:
        pass

def disable_dpms():
    try:
        subprocess.call(["xset", "-dpms"], stdout=DEVNULL, stderr=DEVNULL)
    except Exception:
        pass

# ---------------------------
# Funções de toggle (usam widgets passados)
# ---------------------------
def toggle_shutdown(button, entry):
    text = entry.get_text().strip()
    try:
        t = int(text)
        if t <= 0:
            raise ValueError
    except Exception:
        subprocess.Popen(["notify-send", "Auto-Desligamento", "Tempo inválido (use inteiro > 0)"])
        return

    if is_xautolock_running():
        stop_xautolock()
        button.set_label("Ativar Auto-Desligamento")
        subprocess.Popen(["notify-send", "Auto-Desligamento", "Desativado"])
        config["shutdown_active"] = False
    else:
        start_xautolock(t)
        button.set_label("Desativar Auto-Desligamento")
        subprocess.Popen(["notify-send", "Auto-Desligamento", f"Ativado: desliga após {t} minutos"])
        config["shutdown_active"] = True
        config["shutdown_time"] = t
    save_config()

def toggle_screen(button, entry):
    text = entry.get_text().strip()
    try:
        t = int(text)
        if t <= 0:
            raise ValueError
    except Exception:
        subprocess.Popen(["notify-send", "Tela", "Tempo inválido (use inteiro > 0)"])
        return

    if is_dpms_enabled():
        disable_dpms()
        button.set_label("Ativar Desligamento da Tela")
        subprocess.Popen(["notify-send", "Tela", "Desligamento de tela desativado"])
        config["screen_active"] = False
    else:
        enable_dpms(t)
        button.set_label("Desativar Desligamento da Tela")
        subprocess.Popen(["notify-send", "Tela", f"Desligamento da tela após {t} minutos"])
        config["screen_active"] = True
        config["screen_off_time"] = t
    save_config()

# ---------------------------
# Construção da GUI
# ---------------------------
# Janela principal
window = Gtk.Window(title="Configurações Auto-Desligamento")
window.set_border_width(10)
window.set_resizable(False)
window.set_default_size(800, 600)                 # ajustar tamanho aqui
window.set_position(Gtk.WindowPosition.CENTER)    # centralizar

# Tenta definir WM class para que wmctrl detecte:
try:
    # primeira string é name, segunda é class
    window.set_wmclass("AutoShutdown", "AutoShutdown")
except Exception:
    # alguns bindings/versões podem não suportar — não crítico
    pass

# Grid e widgets
grid = Gtk.Grid()
grid.set_row_spacing(10)
grid.set_column_spacing(10)
window.add(grid)

# Auto-Desligamento
label_shutdown = Gtk.Label(label="Minutos para Auto-Desligamento:")
entry_shutdown = Gtk.Entry()
entry_shutdown.set_text(str(config.get("shutdown_time", 30)))
button_shutdown = Gtk.Button()
button_shutdown.set_label("Desativar Auto-Desligamento" if config.get("shutdown_active") else "Ativar Auto-Desligamento")
button_shutdown.connect("clicked", toggle_shutdown, entry_shutdown)

grid.attach(label_shutdown, 0, 0, 1, 1)
grid.attach(entry_shutdown, 1, 0, 1, 1)
grid.attach(button_shutdown, 2, 0, 1, 1)

# Desligamento da Tela
label_screen = Gtk.Label(label="Minutos para Desligar a Tela:")
entry_screen = Gtk.Entry()
entry_screen.set_text(str(config.get("screen_off_time", 10)))
button_screen = Gtk.Button()
button_screen.set_label("Desativar Desligamento da Tela" if config.get("screen_active") else "Ativar Desligamento da Tela")
button_screen.connect("clicked", toggle_screen, entry_screen)

grid.attach(label_screen, 0, 1, 1, 1)
grid.attach(entry_screen, 1, 1, 1, 1)
grid.attach(button_screen, 2, 1, 1, 1)

# ---------------------------
# Restaurar estado salvo ao abrir (após widgets existirem)
# ---------------------------
def restore_state():
    # restaurar auto-desligamento
    try:
        if config.get("shutdown_active"):
            if not is_xautolock_running():
                start_xautolock(int(config.get("shutdown_time", 30)))
            button_shutdown.set_label("Desativar Auto-Desligamento")
    except Exception:
        pass
    # restaurar screen DPMS
    try:
        if config.get("screen_active"):
            enable_dpms(int(config.get("screen_off_time", 10)))
            button_screen.set_label("Desativar Desligamento da Tela")
    except Exception:
        pass

restore_state()

# ---------------------------
# Conexão de encerramento: remove lockfile e fecha o loop GTK
# ---------------------------
def on_destroy(widget):
    try:
        remove_lockfile()
    finally:
        Gtk.main_quit()

window.connect("destroy", on_destroy)

# Mostrar e executar
window.show_all()
Gtk.main()
