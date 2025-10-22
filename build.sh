#!/bin/bash
# Render build script for Amazon Gemini Scraper
# This script is optional - Render will use Dockerfile by default

set -e

echo "🔨 Starting Render build process..."

# Update pip and build tools
echo "📦 Updating pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium --with-deps

echo "✅ Build completed successfully!"
