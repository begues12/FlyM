#!/bin/bash

##############################################################################
# Instalar FlyM como servicio systemd
# Esto permite que FlyM inicie automáticamente al arrancar
##############################################################################

echo "Instalando FlyM como servicio systemd..."

# Copiar archivo de servicio
sudo cp "$(dirname "$0")/systemd/flym.service" /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar servicio
sudo systemctl enable flym.service

echo ""
echo "Servicio instalado. Comandos útiles:"
echo "  sudo systemctl start flym     - Iniciar servicio"
echo "  sudo systemctl stop flym      - Detener servicio"
echo "  sudo systemctl status flym    - Ver estado"
echo "  sudo systemctl restart flym   - Reiniciar"
echo "  sudo journalctl -u flym -f    - Ver logs en vivo"
echo ""
