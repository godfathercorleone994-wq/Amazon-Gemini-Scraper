.PHONY: help install run test clean docker-up docker-down format lint

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m

help: ## Show this help message
	@echo "${GREEN}Available commands:${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${YELLOW}%-20s${NC} %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "${GREEN}Installing dependencies...${NC}"
	pip install -r requirements.txt
	playwright install chromium
	pre-commit install

run: ## Run the application
	@echo "${GREEN}Starting application...${NC}"
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-celery: ## Run Celery worker
	@echo "${GREEN}Starting Celery worker...${NC}"
	celery -A workers.celery_app worker --loglevel=info

run-flower: ## Run Flower (Celery monitoring)
	@echo "${GREEN}Starting Flower...${NC}"
	celery -A workers.celery_app flower

run-dashboard: ## Run Streamlit dashboard
	@echo "${GREEN}Starting Dashboard...${NC}"
	streamlit run features/dashboard/streamlit_app.py

test: ## Run tests
	@echo "${GREEN}Running tests...${NC}"
	pytest tests/ -v --cov=. --cov-report=html

test-unit: ## Run unit tests only
	@echo "${GREEN}Running unit tests...${NC}"
	pytest tests/unit/ -v

test-integration: ## Run integration tests
	@echo "${GREEN}Running integration tests...${NC}"
	pytest tests/integration/ -v

format: ## Format code with black
	@echo "${GREEN}Formatting code...${NC}"
	black .
	ruff . --fix

lint: ## Lint code
	@echo "${GREEN}Linting code...${NC}"
	ruff .
	mypy .

clean: ## Clean cache files
	@echo "${RED}Cleaning cache files...${NC}"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

docker-build: ## Build Docker images
	@echo "${GREEN}Building Docker images...${NC}"
	docker-compose build

docker-up: ## Start Docker containers
	@echo "${GREEN}Starting Docker containers...${NC}"
	docker-compose up -d

docker-down: ## Stop Docker containers
	@echo "${RED}Stopping Docker containers...${NC}"
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

migrate: ## Run database migrations
	@echo "${GREEN}Running migrations...${NC}"
	python scripts/migrate_db.py

seed: ## Seed database with sample data
	@echo "${GREEN}Seeding database...${NC}"
	python scripts/seed_data.py

backup: ## Backup database
	@echo "${GREEN}Backing up database...${NC}"
	python scripts/backup_db.py
