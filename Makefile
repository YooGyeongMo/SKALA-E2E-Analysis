# =====================================================================
# SKALA Day2: Adult Census End2End 분석 파이프라인
# 사용법: make help
# =====================================================================

PYTHON ?= python3.11
VENV   := .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.PHONY: help setup run test lint format schedule hooks clean

help: ## 사용 가능한 타겟 목록
	@awk 'BEGIN {FS = ":.*##"; printf "\n타겟 목록:\n"} /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2} END {print ""}' $(MAKEFILE_LIST)

setup: ## 가상환경 생성 + 의존성 설치 + 패키지 editable 설치
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -q -U pip
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q -e .
	@echo "완료. 다음: make run"

run: ## 파이프라인 전체 실행 (E>V>A>M>Z>R, output/에 산출물 생성)
	$(PY) -m e2e

test: ## pytest 실행 (커버리지 80% 게이트 포함)
	$(PY) -m pytest

lint: ## ruff 검사 + 포맷 확인 + mypy 타입 검사
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts
	$(PY) -m mypy src

format: ## ruff로 코드 자동 정렬
	$(PY) -m ruff format src tests scripts
	$(PY) -m ruff check --fix src tests scripts

schedule: ## 스케줄 실행기 1회 시연 (report.md 재생성 데모)
	$(PY) scripts/schedule_runner.py --once

hooks: ## pre-commit 훅 설치 (커밋 시 자동 품질 검사)
	$(PY) -m pre_commit install

clean: ## 산출물과 캐시 삭제 (재실행하면 전부 재생성됨)
	rm -rf output data/raw .pytest_cache .mypy_cache .ruff_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
