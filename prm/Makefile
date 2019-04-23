# Do not really on artifacts created by make for all targets.
.PHONY: all venv flake8 unit package clean tests check dist

all: venv check dist

venv:
	@echo Preparing virtual enviornment using pipenv.
	pipenv --version
	env PIPENV_QUIET=true pipenv install --dev

flake8: 
	@echo Checking code quality.
	pipenv run flake8 owca tests example workloads

package: 
	@echo Building owca pex file.
	-rm dist/owca-prm.pex
	-rm .pex-build/owca*
	-rm .pex-build/prm*
	-rm -rf prm.egg-info/
	pipenv run env PYTHONPATH=. pex . owca -v --cache-dir=.pex-build --output=dist/owca-prm.pex -m owca.main:main 
	./dist/owca-prm.pex --version


check: flake8

dist: package

clean:
	@echo Cleaning.
	rm -rf .pex-build
	rm -rf prm.egg-info
	rm -rf dist
	pipenv --rm
