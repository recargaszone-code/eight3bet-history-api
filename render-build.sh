#!/usr/bin/env bash
set -e

echo "🛠 Fixando cache do apt (problema comum no Render)..."
rm -rf /var/lib/apt/lists/*
mkdir -p /var/lib/apt/lists/partial

echo "📦 Atualizando pacotes do sistema..."
apt-get update -qq

echo "📦 Instalando dependências do Playwright..."
apt-get install -y -qq --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc-s1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils

echo "🐍 Instalando pacotes Python..."
pip install --no-cache-dir -r requirements.txt

echo "🌐 Instalando Chromium (Playwright)..."
playwright install chromium

echo "✅ Build finalizada com sucesso!"
