#!/bin/bash

sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 xautolock x11-xserver-utils libnotify-bin jq


# Criar pasta ~/bin se não existir
mkdir -p ~/bin

# Copiar arquivos para ~/bin
sudo cp auto-shutdown-config.py ~/bin/
sudo cp auto-shutdown-startup.sh ~/bin/

# Criar pastas para atalhos
mkdir -p ~/.local/share/applications
mkdir -p ~/.config/autostart

# Copiar atalhos e ícone para os lugares certos
cp auto-shutdown-config.desktop ~/.local/share/applications/
cp icone.png ~/.local/share/applications/  # ícone para o atalho python

cp auto-shutdown-startup.desktop ~/.config/autostart/

echo "Arquivos e atalhos instalados com sucesso!"

