.PHONY: dev dev-down build seed logs logs-backend logs-notification status clean rebuild

dev:
	@echo "🎱 Starting Bida Cao Cap E-commerce Stack..."
	docker-compose up -d --build
	@echo "✅ Stack running!"
	@echo "   Frontend: http://localhost"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

dev-down:
	@echo "🛑 Stopping stack..."
	docker-compose down

seed:
	@echo "🌱 Seeding sample data..."
	docker-compose exec catalog-service python seed.py

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-notification:
	docker-compose logs -f notification-worker

status:
	docker-compose ps

clean:
	@echo "🧹 Cleaning all data..."
	docker-compose down -v
	@echo "✅ All volumes removed"

rebuild:
	docker-compose down
	docker-compose up -d --build
