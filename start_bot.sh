#!/bin/bash
# Startup script for Amazon Scraper Telegram Bot

echo "🤖 Amazon Scraper Telegram Bot - Startup Script"
echo "================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your credentials:"
    echo "  cp .env.example .env"
    echo ""
    echo "Required variables:"
    echo "  - TELEGRAM_BOT_TOKEN (get from @BotFather on Telegram)"
    echo "  - MONGODB_ATLAS_URI"
    echo "  - REDIS_URL"
    echo "  - GEMINI_API_KEY"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python3 -c "import telegram" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "🎭 Installing Playwright browsers..."
    playwright install chromium
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Check TELEGRAM_BOT_TOKEN
if ! grep -q "TELEGRAM_BOT_TOKEN=your-telegram-bot-token" .env && grep -q "TELEGRAM_BOT_TOKEN=" .env; then
    echo "✅ TELEGRAM_BOT_TOKEN configured"
else
    echo "⚠️  Warning: TELEGRAM_BOT_TOKEN may not be configured"
    echo "   Please set it in .env file"
fi

echo ""
echo "🚀 Starting bot..."
echo "================================================"
echo ""

# Run the bot
python3 bot_main.py
