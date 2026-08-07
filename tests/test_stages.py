"""단계별 단위 테스트: extract 캐시, clean 정제, stats 검정, model 학습."""

from pathlib import Path

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.extract import extract
from e2e.model import train_and_save
from e2e.stats import analyze


def test_extract_uses_cache(test_config: AppConfig) -> None:
    """캐시 파일이 있으면 네트워크 없이 그 경로를 반환한다(멱등성)."""
    path = extract(test_config)  # fixture_csv가 이미 존재하므로 다운로드 없음
    assert path == test_config.data.raw_path
    assert path.exists()


def test_clean_detects_missing_and_dupes(test_config: AppConfig) -> None:
    """공백 섞인 ' ?' 토큰이 결측으로 잡히고 중복이 제거된다."""
    df, meta = load_and_clean(test_config)
    assert meta["missing_cells"] > 0, "na_token='?'이면 결측이 반드시 잡혀야 한다"
    assert meta["duplicate_rows"] >= 1  # conftest가 중복 1행을 심었다
    assert meta["rows_clean"] == len(df)
    assert not df.isna().any().any()
    assert not df.duplicated().any()


def test_analyze_finds_planted_signal(test_config: AppConfig) -> None:
    """합성 데이터에 심어 둔 그룹 차이(35 vs 45시간)를 검정이 잡아낸다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    assert result["significant"] is True
    assert result["p_value"] < 0.001
    assert result["cohens_d"] > 0.8  # 10시간 차이를 심었으므로 큰 효과여야 한다
    assert len(result["group_stats"]) == 2


def test_model_trains_and_reloads(test_config: AppConfig) -> None:
    """Pipeline이 학습되고, 저장 후 재로딩한 모델의 예측이 일치한다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    assert 0.0 <= result["accuracy"] <= 1.0
    assert 0.0 <= result["f1"] <= 1.0
    assert result["reload_ok"] is True
    assert Path(result["model_path"]).exists()
