.PHONY: serve

serve:
	@echo "🛜 Starting local development server..."
	@python -m http.server -d html 8000