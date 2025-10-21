FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install system dependencies for Playwright
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .

# Update build tools to avoid metadata-generation-failed errors
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install all requirements at once for better caching
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and install Playwright browsers
COPY . .
RUN playwright install chromium && \
    playwright install-deps chromium

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

EXPOSE ${PORT}

# Use shell form to allow environment variable expansion
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
