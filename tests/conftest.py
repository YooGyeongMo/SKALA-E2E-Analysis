"""테스트 공용 픽스처.

네트워크 없이 전 단계를 검증하기 위해 Adult와 같은 스키마의 합성
CSV(400행)를 생성한다. 소득 그룹 간 근로시간에 의도적으로 차이를
심어 두어(35 vs 45 중심) 검정과 모델이 신호를 잡는지 확인한다.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from e2e.config import AppConfig, load_config

COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education-num",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
    "native-country",
    "income",
]


def _make_row(rng: np.random.Generator, income: str) -> list[str]:
    hours = rng.normal(45 if income == ">50K" else 35, 5)
    return [
        str(int(rng.integers(20, 65))),
        rng.choice(["Private", "State-gov", "?"], p=[0.85, 0.1, 0.05]),
        str(int(rng.integers(10000, 999999))),
        rng.choice(["Bachelors", "HS-grad", "Masters"]),
        str(int(rng.integers(1, 16))),
        rng.choice(["Married-civ-spouse", "Never-married"]),
        rng.choice(["Tech-support", "Sales", "Exec-managerial"]),
        rng.choice(["Husband", "Not-in-family"]),
        rng.choice(["White", "Black", "Asian-Pac-Islander"]),
        rng.choice(["Male", "Female"]),
        "0",
        "0",
        str(int(max(1, min(99, hours)))),
        rng.choice(["United-States", "Korea"]),
        income,
    ]


@pytest.fixture(scope="session")
def fixture_csv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Adult 스키마의 합성 원천 CSV. 원본처럼 값 앞에 공백을 넣는다."""
    rng = np.random.default_rng(42)
    rows = [_make_row(rng, ">50K" if i % 4 == 0 else "<=50K") for i in range(400)]
    rows.append(rows[0])  # 중복 1행을 의도적으로 심는다
    path = tmp_path_factory.mktemp("raw") / "adult.csv"
    lines = [", ".join(r) for r in rows]  # 원본과 동일하게 쉼표 뒤 공백
    # 원본 adult.data처럼 파일 끝에 빈 줄을 둔다: Pandas는 건너뛰고 Polars는
    # null 행으로 읽는 함정(#11)을 테스트가 재현하도록 하기 위함
    path.write_text("\n".join(lines) + "\n\n", encoding="utf-8")
    return path


@pytest.fixture()
def test_config(fixture_csv: Path, tmp_path: Path) -> AppConfig:
    """실제 config.yaml을 로딩한 뒤 경로만 테스트용으로 바꾼다.

    실제 파일을 기반으로 하는 이유: config.yaml 자체의 유효성도
    함께 검증되기 때문(설정 파일이 깨지면 여기서 바로 실패한다).
    """
    project_root = Path(__file__).resolve().parents[1]
    with open(project_root / "config.yaml", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    raw["data"]["raw_path"] = str(fixture_csv)
    out = tmp_path / "output"
    raw["output"] = {
        "dir": str(out),
        "figures_dir": str(out / "figures"),
        "report_path": str(out / "report.md"),
        "model_path": str(out / "model.joblib"),
    }
    return AppConfig.model_validate(raw)


@pytest.fixture(scope="session")
def real_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config.yaml"


@pytest.fixture()
def real_config(real_config_path: Path) -> AppConfig:
    return load_config(real_config_path)
