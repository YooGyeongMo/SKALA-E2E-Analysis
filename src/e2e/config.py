"""config.yaml 로딩과 Pydantic 검증.

설정을 코드에서 분리(선언적 관리)하는 이유:
- 데이터셋 교체, 파라미터 변경이 코드 수정 없이 가능하다
- 잘못된 설정(오타, 범위 밖 값)이 실행 전에 검증 오류로 즉시 드러난다
- 모든 단계 함수는 AppConfig만 주입받으므로 테스트에서 가짜 설정으로
  쉽게 대체할 수 있다(의존성 주입)
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    name: str
    seed: int = 42


class DataConfig(BaseModel):
    url: str
    raw_path: Path
    na_token: str
    # 외부 검증용 홀드아웃(UCI adult.test): 미지정 시 외부 평가는 생략된다
    test_url: str | None = None
    test_raw_path: Path | None = None
    columns: list[str] = Field(min_length=1)


class AnalysisConfig(BaseModel):
    target: str
    positive_label: str
    hypothesis_feature: str
    alpha: float = Field(gt=0, lt=1)


class ModelConfig(BaseModel):
    test_size: float = Field(gt=0, lt=1)
    numeric_features: list[str] = Field(min_length=1)
    categorical_features: list[str] = Field(min_length=1)


class OutputConfig(BaseModel):
    dir: Path
    figures_dir: Path
    report_path: Path
    model_path: Path


class AppConfig(BaseModel):
    project: ProjectConfig
    data: DataConfig
    analysis: AnalysisConfig
    model: ModelConfig
    output: OutputConfig


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    """config.yaml을 읽어 검증된 AppConfig를 반환한다."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)
