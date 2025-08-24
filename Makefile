.PHONY: help install build start stop clean demo seed-data logs test

help: ## Show this help message
	@echo 'FraudShield - Financial Fraud Detection System'
	@echo '=============================================='
	@echo ''
	@echo 'Available commands:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing Node.js dependencies..."
	cd frontend && npm install
	@echo "Installation complete!"

build: ## Build Docker images
	@echo "Building Docker images..."
	docker-compose build
	@echo "Build complete!"

start: ## Start all services
	@echo "Starting FraudShield services..."
	docker-compose up -d
	@echo "Services started! Access the application at:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  Grafana: http://localhost:3001 (admin/admin)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  MLflow: http://localhost:5000"

stop: ## Stop all services
	@echo "Stopping FraudShield services..."
	docker-compose down
	@echo "Services stopped!"

clean: ## Clean up containers, volumes, and images
	@echo "Cleaning up..."
	docker-compose down -v --rmi all
	docker system prune -f
	@echo "Cleanup complete!"

demo: ## Run the complete demo setup
	@echo "Setting up FraudShield demo..."
	@echo "1. Starting services..."
	docker-compose up -d
	@echo "2. Waiting for services to be ready..."
	@sleep 30
	@echo "3. Seeding sample data..."
	docker-compose exec backend python -m backend.pipeline.seed_data
	@echo "4. Demo setup complete!"
	@echo ""
	@echo "🎉 FraudShield is ready!"
	@echo ""
	@echo "Access the application:"
	@echo "  📊 Dashboard: http://localhost:3000"
	@echo "  🔍 Live Feed: http://localhost:3000/live-feed"
	@echo "  ⚠️  Alerts: http://localhost:3000/alerts"
	@echo "  🧪 Simulator: http://localhost:3000/simulator"
	@echo ""
	@echo "Monitoring:"
	@echo "  📈 Grafana: http://localhost:3001 (admin/admin)"
	@echo "  📊 Prometheus: http://localhost:9090"
	@echo "  🔬 MLflow: http://localhost:5000"
	@echo ""
	@echo "Try the simulator to test fraud scenarios!"

seed-data: ## Seed the database with sample data
	@echo "Seeding database with sample data..."
	docker-compose exec backend python -m backend.pipeline.seed_data
	@echo "Data seeding complete!"

logs: ## Show logs from all services
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

test: ## Run tests
	@echo "Running tests..."
	pytest tests/ -v
	@echo "Tests complete!"

health: ## Check system health
	@echo "Checking system health..."
	@curl -s http://localhost:8000/health | jq . || echo "Backend not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend: Not responding"
	@curl -s http://localhost:3001 > /dev/null && echo "Grafana: OK" || echo "Grafana: Not responding"

restart: ## Restart all services
	@echo "Restarting services..."
	docker-compose restart
	@echo "Services restarted!"

dev: ## Start development mode
	@echo "Starting development mode..."
	docker-compose up -d postgres kafka
	@echo "Starting backend in development mode..."
	cd backend && uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend in development mode..."
	cd frontend && npm start &
	@echo "Development mode started!"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
