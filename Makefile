PYTHON ?= ./.venv/bin/python
PYTEST_ARGS ?= -q
TESTS ?= tests

.PHONY: test integration api

test:
	$(PYTHON) -m pytest $(PYTEST_ARGS) $(TESTS)

integration:
	$(PYTHON) -m pytest $(PYTEST_ARGS) tests/integration

api:
	$(PYTHON) -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
