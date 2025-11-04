

clean: ## Очистить кэши, coverage и сборочные артефакты
	$(Q)echo "🧺 Cleaning caches..."
	$(Q)find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	$(Q)rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov build dist *.egg-info
