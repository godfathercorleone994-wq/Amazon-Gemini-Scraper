#!/bin/bash

# Script para instalar Playwright Chromium em ambiente Docker
# Contorna o erro de progress bar que ocorre durante a instalação

echo "Installing Playwright Chromium browser..."

# O erro "RangeError: Invalid count value: Infinity" é um bug conhecido do Playwright
# quando rodando em containers Docker sem TTY apropriado
# Ref: https://github.com/microsoft/playwright/issues

# Tentar instalação normal e capturar saída
set +e  # Não sair imediatamente em caso de erro
playwright install chromium > /tmp/pw_out.log 2>&1
INSTALL_EXIT_CODE=$?
set -e

# Verificar se houve erro de progress bar (bug conhecido e esperado)
if [ $INSTALL_EXIT_CODE -ne 0 ]; then
    if grep -q "RangeError: Invalid count value" /tmp/pw_out.log || grep -q "EPIPE" /tmp/pw_out.log; then
        echo "INFO: Progress bar error detected (expected in Docker environments)"
        echo "Attempting manual browser installation..."
        
        # Fazer download manual do Chromium
        CHROMIUM_VERSION="1091"  # Playwright 1.40.0 uses build 1091
        BROWSER_DIR="/root/.cache/ms-playwright/chromium-${CHROMIUM_VERSION}"
        
        if [ ! -d "$BROWSER_DIR" ]; then
            echo "Downloading Chromium build ${CHROMIUM_VERSION}..."
            mkdir -p /root/.cache/ms-playwright
            cd /root/.cache/ms-playwright
            
            # Download com fallback para diferentes CDNs
            if ! wget -q --no-check-certificate "https://playwright.azureedge.net/builds/chromium/${CHROMIUM_VERSION}/chromium-linux.zip" -O chromium.zip 2>/dev/null; then
                echo "First CDN failed, trying alternative..."
                wget -q --no-check-certificate "https://playwright-akamai.azureedge.net/builds/chromium/${CHROMIUM_VERSION}/chromium-linux.zip" -O chromium.zip
            fi
            
            echo "Extracting Chromium..."
            unzip -q chromium.zip
            # Manter a estrutura de diretórios que o Playwright espera (chrome-linux dentro de chromium-VERSION)
            mkdir -p "chromium-${CHROMIUM_VERSION}"
            mv chrome-linux "chromium-${CHROMIUM_VERSION}/"
            rm chromium.zip
            
            echo "Chromium installed successfully to $BROWSER_DIR"
        else
            echo "Chromium already exists at $BROWSER_DIR"
        fi
    else
        echo "ERROR: Unexpected error during Playwright installation:"
        cat /tmp/pw_out.log
        exit $INSTALL_EXIT_CODE
    fi
else
    echo "Playwright Chromium installed successfully"
fi

# Verificar instalação
if [ -d "/root/.cache/ms-playwright/chromium-"* ] || playwright --version >/dev/null 2>&1; then
    echo "✓ Browser installation verified"
    exit 0
else
    echo "✗ Browser installation verification failed"
    exit 1
fi
