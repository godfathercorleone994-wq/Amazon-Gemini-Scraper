FROM python:3.14.0

# --- Sistema básico + dependências Playwright ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
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
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    fonts-unifont \
    gcc \
    g++ \
    python3-dev \
    libyaml-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Copiar e instalar dependências Python ---
COPY requirements.txt .

# atualiza ferramentas de build para evitar “metadata‑generation‑failed”
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --upgrade pip setuptools wheel


# instala dependências Python (usando --trusted-host para resolver problemas de SSL)
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# --- Copiar código e instalar navegadores Playwright ---
COPY . .
COPY install_playwright.sh /tmp/install_playwright.sh
RUN chmod +x /tmp/install_playwright.sh
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
ENV NODE_TLS_REJECT_UNAUTHORIZED=0
# Instalar navegadores usando script que trata o erro de progress bar
RUN /tmp/install_playwright.sh

EXPOSE 8000

# Use shell form to allow environment variable expansion
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
