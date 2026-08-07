"""분석 v3 검증: 분포 보존, class_weight 실험, 교란변수 통제."""

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.model import train_and_save
from e2e.stats import CONFOUNDERS, analyze


def test_preservation_metrics_reported(test_config: AppConfig) -> None:
    """정제 전후의 타깃 비율과 가설 변수 분포가 메타에 담긴다."""
    _, meta = load_and_clean(test_config)
    p = meta["preservation"]
    assert 0.0 <= p["positive_ratio_before"] <= 100.0
    assert 0.0 <= p["positive_ratio_after"] <= 100.0
    assert p["ratio_shift_pp"] >= 0.0
    assert p["feature_mean_before"] > 0
    assert p["feature_median_before"] > 0


def test_preservation_small_shift_on_random_missing(test_config: AppConfig) -> None:
    """결측이 소득과 무관하게 심어진 합성 데이터에서는 비율 변화가 작아야 한다."""
    _, meta = load_and_clean(test_config)
    # 픽스처의 결측(workclass '?')은 소득과 독립이므로 큰 왜곡이 없어야 정상
    assert meta["preservation"]["ratio_shift_pp"] < 5.0


def test_balanced_model_tradeoff(test_config: AppConfig) -> None:
    """balanced 모델이 비교표에 있고 기본형보다 recall이 낮지 않다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    rows = {row["name"]: row for row in result["comparison"]}
    assert "LogReg(balanced)" in rows
    assert rows["LogReg(balanced)"]["recall"] >= rows["LogisticRegression"]["recall"]
    for row in result["comparison"]:
        assert 0.0 <= row["recall"] <= 1.0


def test_confounder_control_keeps_planted_effect(test_config: AppConfig) -> None:
    """심어 둔 근로시간 신호가 연령/교육 통제 후에도 유의하게 남는다.

    픽스처에서 연령과 교육은 소득과 독립으로 생성되므로, 통제를 넣어도
    근로시간의 오즈비는 1보다 크고 유의해야 한다.
    """
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    conf = result["confounder"]
    assert conf["predictors"] == [test_config.analysis.hypothesis_feature, *CONFOUNDERS]
    feature_row = conf["rows"][0]
    assert feature_row["significant"] is True
    assert feature_row["odds"] > 1.0
    assert feature_row["ci_low"] > 1.0, "신뢰구간이 1을 포함하면 효과 소멸"
    assert conf["n"] == len(df)
