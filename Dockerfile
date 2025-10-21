FROM python:3.11-slim

# --- Sistema básico + dependências Playwright ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    fonts-unifont \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libdbus-1-3 \
    libglib2.0-0 \
    libegl1 \
    libnotify4 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libopus0 \
    libwoff1 \
    libharfbuzz-icu0 \
    libhyphen0 \
    libmanette-0.2-0 \
    libgles2 \
    gstreamer1.0-libav \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    libenchant-2-2 \
    libsecret-1-0 \
    libvpx9 \
    libevdev2 \
    libxkbfile1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Copiar e instalar dependências Python ---
COPY requirements.txt .

# atualiza ferramentas de build para evitar “metadata‑generation‑failed”
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# mostra exatamente o pacote que falhar
RUN set -eux; \
    while read -r line || [ -n "$line" ]; do \
        echo "=== Instalando: $line ==="; \
        pip install "$line"; \
    done < requirements.txt

# --- Copiar código e instalar navegadores Playwright ---
COPY . .
RUN playwright install chromium

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
