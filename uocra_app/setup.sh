#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# UOCRA Sistema — Script de instalación en Ubuntu
# Ejecutar como: sudo bash setup.sh
# ═══════════════════════════════════════════════════════════════

set -e
APP_DIR="/opt/uocra"
APP_USER="uocra"
PORT=8000

echo "=== UOCRA Sistema — Instalación ==="

# 1. Dependencias del sistema
echo "[1/6] Instalando dependencias..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx

# 2. Crear usuario y directorio
echo "[2/6] Configurando usuario y directorio..."
id -u $APP_USER &>/dev/null || useradd -r -s /bin/false $APP_USER
mkdir -p $APP_DIR
cp -r . $APP_DIR/
chown -R $APP_USER:$APP_USER $APP_DIR

# 3. Entorno virtual e instalar dependencias Python
echo "[3/6] Instalando dependencias Python..."
python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install -q -r $APP_DIR/requirements.txt

# 4. Inicializar base de datos
echo "[4/6] Inicializando base de datos..."
cd $APP_DIR
$APP_DIR/venv/bin/python -c "from models import init_db; init_db(); print('DB OK')"

# 5. Crear servicio systemd
echo "[5/6] Configurando servicio systemd..."
cat > /etc/systemd/system/uocra.service << EOF
[Unit]
Description=UOCRA Sistema — CL Gestión
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
ExecStart=$APP_DIR/venv/bin/gunicorn -w 2 -b 127.0.0.1:$PORT app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable uocra
systemctl restart uocra

# 6. Configurar Nginx
echo "[6/6] Configurando Nginx..."
cat > /etc/nginx/sites-available/uocra << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    client_max_body_size 10M;
}
EOF

ln -sf /etc/nginx/sites-available/uocra /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "=== Instalación completa ==="
echo ""
echo "URL:    http://TU-IP-DEL-SERVIDOR"
echo ""
echo "Usuarios iniciales:"
echo "  Estudio 1: clgest@gmail.com   / lescgo1"
echo "  Estudio 2: clgestad@gmail.com / lescgo2"
echo ""
echo "Para agregar HTTPS con dominio propio:"
echo "  apt install certbot python3-certbot-nginx"
echo "  certbot --nginx -d tudominio.com"
echo ""
echo "Para ver logs:"
echo "  journalctl -u uocra -f"
