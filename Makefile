.PHONY: test image preflight run

test:
	uv run python -m unittest discover -s tests

image:
	docker build -t autoquant-research:latest .

preflight:
	@test -n "$(MANIFEST)" || (echo "MANIFEST is required"; exit 2)
	uv run python daily_controller.py --manifest $(MANIFEST) --dry-run

run:
	@test -n "$(MANIFEST)" || (echo "MANIFEST is required"; exit 2)
	uv run python daily_controller.py --manifest $(MANIFEST)
