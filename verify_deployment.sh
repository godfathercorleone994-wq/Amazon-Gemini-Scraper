#!/bin/bash
# Deployment Verification Script
# Run this script after deploying to Railway to verify everything works

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Railway Deployment Verification${NC}"
echo "=========================================="

# Check if URL is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Please provide your Railway app URL${NC}"
    echo "Usage: ./verify_deployment.sh https://your-app.railway.app"
    exit 1
fi

APP_URL=$1
# Remove trailing slash if present
APP_URL=${APP_URL%/}

echo -e "\n${YELLOW}Testing URL: ${APP_URL}${NC}\n"

# Test 1: Root endpoint
echo -e "${YELLOW}1. Testing root endpoint...${NC}"
if curl -s -f "${APP_URL}/" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Root endpoint is accessible${NC}"
else
    echo -e "${RED}❌ Root endpoint failed${NC}"
    exit 1
fi

# Test 2: Health check
echo -e "\n${YELLOW}2. Testing health check...${NC}"
HEALTH_RESPONSE=$(curl -s "${APP_URL}/api/v1/health")
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test 3: Liveness probe
echo -e "\n${YELLOW}3. Testing liveness probe...${NC}"
if curl -s -f "${APP_URL}/api/v1/health/live" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Liveness probe passed${NC}"
else
    echo -e "${RED}❌ Liveness probe failed${NC}"
fi

# Test 4: Readiness probe
echo -e "\n${YELLOW}4. Testing readiness probe...${NC}"
READY_RESPONSE=$(curl -s -w "\n%{http_code}" "${APP_URL}/api/v1/health/ready")
HTTP_CODE=$(echo "$READY_RESPONSE" | tail -n 1)
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 503 ]; then
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo -e "${GREEN}✅ Readiness probe passed (all services ready)${NC}"
    else
        echo -e "${YELLOW}⚠️  Readiness probe returned 503 (services not ready)${NC}"
        echo "This is normal if MongoDB or Redis are not connected yet"
    fi
else
    echo -e "${RED}❌ Readiness probe failed with HTTP $HTTP_CODE${NC}"
fi

# Test 5: API documentation
echo -e "\n${YELLOW}5. Testing API documentation...${NC}"
if curl -s -f "${APP_URL}/api/v1/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API documentation is accessible${NC}"
    echo "Visit: ${APP_URL}/api/v1/docs"
else
    echo -e "${RED}❌ API documentation failed${NC}"
fi

# Test 6: API info endpoint
echo -e "\n${YELLOW}6. Testing API info...${NC}"
INFO_RESPONSE=$(curl -s "${APP_URL}/api/v1/info")
if echo "$INFO_RESPONSE" | grep -q '"name"'; then
    echo -e "${GREEN}✅ API info endpoint working${NC}"
    echo "Response: $INFO_RESPONSE"
else
    echo -e "${RED}❌ API info endpoint failed${NC}"
fi

# Summary
echo -e "\n=========================================="
echo -e "${GREEN}🎉 Deployment verification complete!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Visit your API docs: ${APP_URL}/api/v1/docs"
echo "2. Test scraping endpoint with a real Amazon URL"
echo "3. Configure notifications (Telegram, Discord, Email)"
echo "4. Set up monitoring and alerts"
echo "5. Review logs in Railway dashboard"
echo ""
echo -e "${YELLOW}Useful endpoints:${NC}"
echo "- Health: ${APP_URL}/api/v1/health"
echo "- API Docs: ${APP_URL}/api/v1/docs"
echo "- Info: ${APP_URL}/api/v1/info"
echo ""
echo -e "${YELLOW}Test scraping (replace PRODUCT_ID):${NC}"
echo "curl -X POST '${APP_URL}/api/v1/scraping/scrape' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"url\": \"https://www.amazon.com/dp/PRODUCT_ID\"}'"
