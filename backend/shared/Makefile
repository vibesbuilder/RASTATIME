all: lint test

include ../tools/python.mk

PIP_INSTALL = --editable .[dev]
PYLINT_ARG = rastatime_shared tests
MYPY_ARG = rastatime_shared
BANDIT_ARG := rastatime_shared

format: .format
lint: .format-check .pylint .mypy .bandit
test: .pytest
test-coverage: .coverage
clean: .clean
