"""분석 v2 검증: 비율 검정, 신뢰구간, 방향 일치, 교차검증, 외부 검증, 오즈비."""

from pathlib import Path

import pytest

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.model import train_and_save
from e2e.stats import analyze


def test_overtime_proportion_test(test_config: AppConfig) -> None:
    """심어 둔 신호(35 vs 45시간)가 초과근무 비율 차이로도 검정된다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    over = result["overtime"]
    assert over["threshold"] == 40
    assert over["significant"] is True
    rates = list(over["rates"].values())
    assert rates[1] > rates[0], "고소득 그룹(45시간 중심)의 초과 비율이 더 높아야 한다"


def test_confidence_interval_excludes_zero(test_config: AppConfig) -> None:
    """평균 차이의 95% CI가 0을 포함하지 않는다(유의성 판정과 일관)."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    assert result["ci_low"] < result["ci_high"]
    assert result["ci_low"] > 0 or result["ci_high"] < 0
    # CI 중심이 평균 차이와 일치하는지(부호 무시) 검산
    center = abs((result["ci_low"] + result["ci_high"]) / 2)
    assert center == pytest.approx(result["mean_diff"], abs=0.02)


def test_cross_check_includes_direction(test_config: AppConfig) -> None:
    """교차검증 판정이 유의성뿐 아니라 방향(부호) 일치까지 본다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    assert result["cross_consistent"] is True


def test_two_group_assertion(test_config: AppConfig) -> None:
    """타깃이 3그룹이 되면 조용히 무시하지 않고 즉시 실패한다."""
    df, _ = load_and_clean(test_config)
    df.loc[df.index[:5], test_config.analysis.target] = "중간소득"
    with pytest.raises(AssertionError, match="2개"):
        analyze(test_config, df)


def test_cross_validation_reported(test_config: AppConfig) -> None:
    """Stratified 5-fold 결과(평균과 표준편차)가 보고된다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    cv = result["cv"]
    assert cv["folds"] == 5
    assert 0.0 <= cv["accuracy_mean"] <= 1.0
    assert cv["accuracy_std"] >= 0.0
    assert 0.0 <= cv["f1_mean"] <= 1.0


def test_external_holdout_with_trap_fixture(test_config: AppConfig, external_csv: Path) -> None:
    """주석행과 라벨 마침표 함정이 있는 외부 파일을 올바르게 평가한다."""
    test_config.data.test_raw_path = external_csv
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    external = result["external"]
    assert external is not None
    assert external["rows"] > 0
    assert 0.0 <= external["accuracy"] <= 1.0
    # 마침표가 제거되지 않으면 라벨 불일치로 정확도가 0 근처로 무너진다.
    # 학습과 같은 생성 규칙의 데이터이므로 우연 수준(0.5)보다 높아야 한다
    assert external["accuracy"] > 0.5


def test_external_skipped_when_absent(test_config: AppConfig) -> None:
    """외부 파일이 없으면 평가를 생략하고 None을 반환한다(선택 사항)."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    assert result["external"] is None


def test_odds_ratios_shape(test_config: AppConfig) -> None:
    """오즈비 상위/하위 목록이 생성되고 정렬이 올바르다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    odds = result["odds"]
    assert len(odds["top"]) == 5 and len(odds["bottom"]) == 5
    assert odds["top"][0]["odds"] >= odds["top"][-1]["odds"]
    assert odds["bottom"][0]["odds"] <= odds["bottom"][-1]["odds"]
    assert odds["top"][0]["odds"] > odds["bottom"][0]["odds"]
