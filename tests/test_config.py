"""config 로딩과 Pydantic 검증 테스트."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from e2e.config import AppConfig, load_config


def test_real_config_loads(real_config_path: Path) -> None:
    """저장소의 config.yaml이 스키마를 통과한다."""
    config = load_config(real_config_path)
    assert config.analysis.target == "income"
    assert config.data.na_token == "?"  # " ?"가 아니어야 결측이 잡힌다
    assert len(config.data.columns) == 15


def test_invalid_alpha_rejected(real_config: AppConfig) -> None:
    """유의수준이 (0, 1) 범위를 벗어나면 실행 전에 검증 오류가 난다."""
    raw = real_config.model_dump()
    raw["analysis"]["alpha"] = 1.5
    with pytest.raises(ValidationError):
        AppConfig.model_validate(raw)


def test_empty_columns_rejected(real_config: AppConfig) -> None:
    """컬럼 목록이 비면 검증 오류가 난다."""
    raw = real_config.model_dump()
    raw["data"]["columns"] = []
    with pytest.raises(ValidationError):
        AppConfig.model_validate(raw)
