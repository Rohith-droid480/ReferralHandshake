.PHONY: all test test-m1a lint up down clean scratch

PYTHON ?= python
PYTEST ?= pytest

all: test-m1a

test:
	$(PYTEST) -v tests/

test-m1a:
	$(PYTEST) -v tests/test_boot_guards.py tests/test_ddl_constraints.py tests/test_tmax_profiles.py

gate-t0:
	$(PYTEST) -v tests/test_race200.py tests/test_mutations.py tests/test_broken_build.py tests/test_witness_merkle.py tests/test_tamper_vs_restore.py tests/test_boot_guards.py tests/test_ddl_constraints.py tests/test_tmax_profiles.py tests/test_pipeline_core.py tests/test_monitor_fold.py

gate-t1:
	$(PYTEST) -v tests/test_judge_join.py tests/test_transport_and_arrivals.py tests/test_dispatcher_proxy_and_replay.py tests/test_cmd_lifecycle.py

gate-t2:
	$(PYTEST) -v tests/test_exotel_ivr.py tests/test_dlt_sms_lint.py tests/test_paper_code_mod37.py tests/test_envelope_crypto.py tests/test_analytics_recompute.py

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
