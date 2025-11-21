#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import subprocess
import os
import psutil
import time
import re
import sys

# --- CONFIGURAÇÕES ---
SCRIPT_PATH = os.path.expanduser("~/auto_off.sh")
PROCESS_NAME = "auto_off.sh"
LOG_FILE = "nohup.out"

class ScriptManagerGUI(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Gerenciador auto_off.sh")
        self.set_border_width(10)
        self.set_default_size(600, 600)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.connect("destroy", Gtk.main_quit)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # ---------------- Tempo para desligar PC ----------------
        label_delay = Gtk.Label(label="Tempo limite para desligar o PC (minutos):")
        label_delay.set_halign(Gtk.Align.START)
        vbox.pack_start(label_delay, False, False, 0)
        
        self.entry_delay = Gtk.Entry()
        self.load_delay_from_script()
        vbox.pack_start(self.entry_delay, False, False, 0)

        # ---------------- Tempo para apagar tela ----------------
        label_tela = Gtk.Label(label="Tempo para apagar a tela (minutos):")
        label_tela.set_halign(Gtk.Align.START)
        vbox.pack_start(label_tela, False, False, 0)

        self.entry_tela = Gtk.Entry()
        self.load_tela_from_script()
        vbox.pack_start(self.entry_tela, False, False, 0)

        # Botão Aplicar
        button_apply = Gtk.Button(label="Aplicar e Reiniciar Script")
        button_apply.connect("clicked", self.on_apply_clicked)
        vbox.pack_start(button_apply, False, False, 0)

        # Interruptor Liga/Desliga
        self.switch = Gtk.Switch()
        self.switch.connect("notify::active", self.on_switch_toggled)
        hbox_switch = Gtk.Box(spacing=10)
        hbox_switch.pack_start(Gtk.Label(label="Script Ativo:"), False, False, 0)
        hbox_switch.pack_start(self.switch, False, False, 0)
        vbox.pack_start(hbox_switch, False, False, 0)

        # Status
        self.status_label = Gtk.Label(label="")
        vbox.pack_start(self.status_label, False, False, 0)
        
        # Inicializa status (bloqueando sinal para evitar loop na inicialização)
        self.switch.handler_block_by_func(self.on_switch_toggled)
        self.update_status_label()
        self.switch.handler_unblock_by_func(self.on_switch_toggled)

    # ----------------------------- LÓGICA -----------------------------

    def get_script_process(self):
        # Itera processos de forma segura ignorando erros de permissão ou processos zumbis
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                # Verifica se cmdline existe e não é None antes de tentar ler
                if proc.info['cmdline'] and PROCESS_NAME in " ".join(proc.info['cmdline']):
                    if proc.pid != os.getpid():
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def kill_script(self):
        proc = self.get_script_process()
        if proc:
            try:
                proc.terminate()
                time.sleep(0.5)
                self.update_status_label(f"Script PID {proc.pid} encerrado.")
            except psutil.NoSuchProcess:
                self.update_status_label("O processo já havia terminado.")
        else:
            self.update_status_label("Script já estava inativo.")

    def run_script(self):
        if self.get_script_process():
            self.update_status_label("Script já está rodando.")
            return

        # Verifica se o arquivo existe antes de tentar rodar
        if not os.path.isfile(SCRIPT_PATH):
            self.update_status_label(f"ERRO: {SCRIPT_PATH} não encontrado!")
            return

        command = f"nohup {SCRIPT_PATH} > {LOG_FILE} 2>&1 &"
        os.system(command)
        
        # Pequena pausa para dar tempo do processo iniciar
        GLib.timeout_add(500, lambda: self.update_status_label("Script iniciado.") or False)

    def update_status_label(self, message=None):
        if message:
            self.status_label.set_text(message)
        
        is_running = bool(self.get_script_process())
        
        # Atualiza o switch sem disparar o evento novamente se já estiver no estado correto
        if self.switch.get_active() != is_running:
            self.switch.handler_block_by_func(self.on_switch_toggled)
            self.switch.set_active(is_running)
            self.switch.handler_unblock_by_func(self.on_switch_toggled)

    # ----------------------------- LEITURA CONFIG -----------------------------

    def load_delay_from_script(self):
        try:
            with open(SCRIPT_PATH, 'r') as f:
                content = f.read()
                match = re.search(r'^LIMITE=(\d+)', content, re.MULTILINE)
                if match:
                    minutes = int(match.group(1)) // 60
                    self.entry_delay.set_text(str(minutes))
        except Exception as e:
            print(f"Erro ao ler LIMITE: {e}")
            self.entry_delay.set_text("0")

    def load_tela_from_script(self):
        try:
            with open(SCRIPT_PATH, 'r') as f:
                content = f.read()
                match = re.search(r'^TELA_LIMITE=(\d+)', content, re.MULTILINE)
                if match:
                    minutes = int(match.group(1)) // 60
                    self.entry_tela.set_text(str(minutes))
        except Exception as e:
            print(f"Erro ao ler TELA_LIMITE: {e}")
            self.entry_tela.set_text("0")

    # ----------------------------- SALVAR CONFIG -----------------------------

    def save_delay_to_script(self, minutes):
        seconds = int(minutes) * 60
        try:
            with open(SCRIPT_PATH, 'r') as f:
                content = f.read()

            new_content = re.sub(
                r'^LIMITE=\d+\s*$',
                f'LIMITE={seconds}',
                content,
                flags=re.MULTILINE
            )

            with open(SCRIPT_PATH, 'w') as f:
                f.write(new_content)

        except Exception as e:
            self.update_status_label(f"ERRO ao salvar config: {e}")

    def save_tela_to_script(self, minutes):
        seconds = int(minutes) * 60
        try:
            with open(SCRIPT_PATH, 'r') as f:
                content = f.read()

            new_content = re.sub(
                r'^TELA_LIMITE=\d+\s*$',
                f'TELA_LIMITE={seconds}',
                content,
                flags=re.MULTILINE
            )

            with open(SCRIPT_PATH, 'w') as f:
                f.write(new_content)

        except Exception as e:
            self.update_status_label(f"ERRO ao salvar config tela: {e}")

    # ----------------------------- EVENTOS -----------------------------

    def on_apply_clicked(self, button):
        minutes_str = self.entry_delay.get_text()
        tela_str = self.entry_tela.get_text()

        if minutes_str.isdigit() and tela_str.isdigit():
            self.save_delay_to_script(minutes_str)
            self.save_tela_to_script(tela_str)

            self.kill_script()
            self.run_script()

            self.update_status_label(
                f"Configurações aplicadas. PC: {minutes_str} min | Tela: {tela_str} min."
            )
        else:
            self.update_status_label("Entrada inválida (use apenas números).")

    def on_switch_toggled(self, switch, gparam):
        if switch.get_active():
            self.run_script()
        else:
            self.kill_script()


# ------------------------------ INSTÂNCIA ÚNICA ------------------------------

def is_already_running(script_name):
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and script_name in " ".join(proc.info['cmdline']):
                if proc.pid != current_pid:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

if __name__ == "__main__":
    script_filename = os.path.basename(__file__)
    if is_already_running(script_filename):
        print(f"Outra instância de '{script_filename}' já está em execução.")
        sys.exit(0)

    win = ScriptManagerGUI()
    win.show_all()
    Gtk.main()
