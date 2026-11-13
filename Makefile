.PHONY: all test test-m1a lint up down clean scratch

PYTHON ?= python
PYTEST ?= pytest

all: test-m1a

test:
	$(PYTEST) -v tests/

test-m1a:
	$(PYTEST) -v tests/test_boot_guards.py tests/test_ddl_constraints.py tests/test_tmax_profiles.py

lint:
	$(PYTHON) -m py_compile api/rhp/*.py tests/*.py

up:
	docker compose up -d

down:
	docker compose down

scratch:
	bash scripts/make_scratch.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
