all: lint test

include ../tools/python.mk

PIP_INSTALL := \
	--editable ../shared \
	--editable .[dev]
PYLINT_ARG := rastatime_api_client tests
MYPY_ARG := rastatime_api_client tests
BANDIT_ARG := rastatime_api_client

format: .format
lint: .format-check .pylint .mypy .bandit
test: .pytest
test-coverage: .coverage
clean: .clean
