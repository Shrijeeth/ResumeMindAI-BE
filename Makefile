.PHONY: help check lint format format-check fix

SRC = .

help:
	@echo "Available targets:"
	@echo "  make check         Run all checks (ruff)"
	@echo "  make lint          Run ruff lint checks"
	@echo "  make format        Auto-format code"
	@echo "  make format-check  Check formatting only"
	@echo "  make fix           Auto-fix lint + format issues"
	@echo "  make test          Run pytest with coverage (fail under 80%)"
	@echo "  make install       Install prod dependencies"
	@echo "  make install-dev   Install prod + dev dependencies"
	@echo "  make install-uv    Install uv"
	@echo "  make install-uv3   Install uv for python3"
	@echo "  make run           Run server"

# ---- Checks ----
check: lint format-check

lint:
	uv run ruff check $(SRC)

format-check:
	uv run ruff format --check $(SRC)

# ---- Fixes ----
format:
	uv run ruff format $(SRC)

fix:
	uv run ruff check $(SRC) --fix
	uv run ruff format $(SRC)

# ---- Tests ----
test:
	uv run pytest --cov=./ --cov-report=term-missing --cov-fail-under=80

# ---- Install Prod/Dev Dependencies ----
install-uv:
	pip install uv

install-uv3:
	pip3 install uv==0.5.0

install:
	uv sync

install-dev:
	uv sync --dev

# ---- Run ----
run:
	uv run main.py
