all: lint

include ../tools/python.mk

PIP_INSTALL := \
	--editable ../shared \
	--editable .[dev,sentry]
PYLINT_ARG := rastatime_api
MYPY_ARG := rastatime_api
BANDIT_ARG := --exclude '*/tests/*' rastatime_api || true

export DJANGO_SETTINGS_MODULE=rastatime_api.settings.testing

format: .format
lint: .format-check .pylint .mypy .bandit
test: .pytest
test-coverage: .coverage
clean: .clean

SCHEMA_FILE ?= schema.yml
schema: $(VENV)
	$(VENV)/bin/rastatime-api spectacular --file $(SCHEMA_FILE)
	if command -v npx > /dev/null; then npx prettier --write $(SCHEMA_FILE); fi

schema-foreach-commit:
	git rebase main -x "$(MAKE) -C api schema"
