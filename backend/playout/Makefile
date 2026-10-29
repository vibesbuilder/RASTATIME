all: lint

include ../tools/python.mk

APP := playout
PIP_INSTALL := \
	--editable ../api-client \
	--editable ../shared \
	--editable .[dev,sentry]
PYLINT_ARG := rastatime_playout tests
MYPY_ARG := rastatime_playout tests || true
BANDIT_ARG := rastatime_playout || true

format: .format
lint: .format-check .pylint .mypy .bandit
test: .pytest
test-coverage: .coverage
clean: .clean

.PHONY: snapshot
snapshot: $(VENV)
	$(VENV)/bin/pytest --snapshot-update
