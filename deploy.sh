#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Argos — Deploy Script para Ubuntu (Hostinger VPS)
# Uso: bash deploy.sh
# ─────────────────────────────────────────────────────────────

set -e

REPO="https://github.com/MykeMDGuimaraes/argos.git"
APP_DIR="/opt/argos"
SERVICE_NAME="argos"
PYTHON="python3"

echo ""
echo "================================================"
echo "  🤖 Argos — Deploy Automático"
echo "================================================"
echo ""

# 1. Dependências do sistema
echo "📦 Instalando dependências do sistema..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git curl

# 2. Clonar ou atualizar repositório
if [ -d "$APP_DIR/.git" ]; then
    echo "🔄 Atualizando repositório..."
    cd "$APP_DIR"
    git pull origin main
else
    echo "📥 Clonando repositório..."
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi

# 3. Ambiente virtual Python
echo "🐍 Configurando ambiente virtual..."
$PYTHON -m venv venv
source venv/bin/activate

# 4. Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip install --quiet --upgrade pip
pip install --quiet \
    langgraph \
    langchain-anthropic \
    langchain-core \
    python-dotenv \
    requests \
    fastapi \
    uvicorn \
    stripe \
    python-telegram-bot

# 5. Criar .env se não existir
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "⚠️  Arquivo .env não encontrado!"
    echo "   Criando a partir do .env.example..."
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "   ‼️  IMPORTANTE: edite o arquivo antes de continuar:"
    echo "   nano $APP_DIR/.env"
    echo ""
fi

# 6. Criar serviço systemd
echo "⚙️  Configurando serviço systemd..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Argos — Agente Conversacional Dia Solutions
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python telegram_bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 7. Habilitar e iniciar serviço
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "================================================"
echo "  ✅ Deploy concluído!"
echo "================================================"
echo ""
echo "Próximos passos:"
echo ""
echo "  1. Edite o .env com suas credenciais:"
echo "     nano $APP_DIR/.env"
echo ""
echo "  2. Inicie o Argos:"
echo "     systemctl start $SERVICE_NAME"
echo ""
echo "  3. Verifique se está rodando:"
echo "     systemctl status $SERVICE_NAME"
echo ""
echo "  4. Acompanhe os logs ao vivo:"
echo "     journalctl -u $SERVICE_NAME -f"
echo ""
