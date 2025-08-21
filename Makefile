# Makefile for Mini Chat
# Provides convenient shortcuts for running the app and tests

.PHONY: help start start:stable start:exp smoke smoke:exp install clean

# Default target
help:
	@echo "Mini Chat - Available commands:"
	@echo ""
	@echo "App Management:"
	@echo "  start:stable    Start app in stable mode (default)"
	@echo "  start:exp       Start app in experimental mode"
	@echo "  install         Install dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  smoke           Run smoke test against stable app"
	@echo "  smoke:exp       Run smoke test against experimental app"
	@echo ""
	@echo "Utilities:"
	@echo "  clean           Clean up temporary files"
	@echo "  help            Show this help message"

# Install dependencies
install:
	pip install -r requirements.txt

# Start app in stable mode (default)
start:stable:
	@echo "🟢 Starting Mini Chat in STABLE mode..."
	EXPERIMENTAL=0 python -m uvicorn src.api:app --reload --port 8000

# Start app in experimental mode
start:exp:
	@echo "🔴 Starting Mini Chat in EXPERIMENTAL mode..."
	EXPERIMENTAL=1 python -m uvicorn src.api:app --reload --port 8000

# Alias for stable mode
start: start:stable

# Run smoke test against stable app
smoke:
	@echo "🧪 Running smoke test against stable app..."
	@if [ -f "scripts/smoke.sh" ]; then \
		chmod +x scripts/smoke.sh && ./scripts/smoke.sh; \
	else \
		echo "Using PowerShell smoke test..."; \
		powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1; \
	fi

# Run smoke test against experimental app
smoke:exp:
	@echo "🧪 Running smoke test against experimental app..."
	@if [ -f "scripts/smoke.sh" ]; then \
		EXPERIMENTAL=1 chmod +x scripts/smoke.sh && EXPERIMENTAL=1 ./scripts/smoke.sh; \
	else \
		echo "Using PowerShell smoke test..."; \
		$env:EXPERIMENTAL="1"; powershell -ExecutionPolicy Bypass -File scripts/smoke.ps1; \
	fi

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete

# Development helpers
dev:setup:
	@echo "Setting up development environment..."
	pip install -r requirements.txt
	python src/ingest.py
	@echo "✅ Development environment ready!"

# Quick test
test:quick:
	@echo "Running quick tests..."
	python -m pytest test_*.py -v --tb=short
