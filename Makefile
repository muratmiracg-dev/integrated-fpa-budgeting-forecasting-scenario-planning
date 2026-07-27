PYTHON ?= python
PYTHONPATH := Python/src

.PHONY: pipeline test lint excel pbip presentations report artifacts

pipeline:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fpa_system.run_pipeline

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check Python

excel:
	node Tools/build_excel.mjs

pbip:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) Tools/build_pbip.py

presentations:
	node Tools/build_presentations.mjs

report:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) Tools/build_vector_report.py

artifacts: pipeline test lint excel pbip presentations report
