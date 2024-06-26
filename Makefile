.DEFAULT_GOAL := help

VENV :=.venv

.PHONY: install
install:  ## Install a virtual environment
	python -m venv ${VENV}
	${VENV}/bin/pip install --upgrade pip
	${VENV}/bin/pip install -r requirements.txt

.PHONY: freeze
freeze: install  ## Freeze all requirements
	${VENV}/bin/pip freeze > requirements_frozen.txt

.PHONY: fmt
fmt: install ## Run autoformatting and linting
	${VENV}/bin/pip install pre-commit
	${VENV}/bin/pre-commit install
	${VENV}/bin/pre-commit run --all-files

.PHONY: clean
clean:  ## Clean up caches and build artifacts
	@git clean -X -d -f

.PHONY: experiments
experiments: install ## Run all experiment
	${VENV}/bin/python experiments.py

.PHONY: help
help:  ## Display this help screen
	@echo -e "\033[1mAvailable commands:\033[0m"
	@grep -E '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' | sort
