"""모델 비교와 평가 리포트 검증."""

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.model import train_and_save


def test_two_models_compared(test_config: AppConfig) -> None:
    """기준선, balanced 실험, RandomForest가 동일 조건에서 비교된다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    names = [row["name"] for row in result["comparison"]]
    assert names == ["LogisticRegression", "LogReg(balanced)", "RandomForest"]
    for row in result["comparison"]:
        assert 0.0 <= row["accuracy"] <= 1.0
        assert 0.0 <= row["f1"] <= 1.0


def test_saved_model_is_baseline(test_config: AppConfig) -> None:
    """저장 모델은 해석 가능한 기준선(LogisticRegression)이다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    assert result["model_name"] == "LogisticRegression"
    assert result["reload_ok"] is True


def test_classification_report_text(test_config: AppConfig) -> None:
    """classification_report가 두 클래스를 모두 포함한다."""
    df, _ = load_and_clean(test_config)
    result = train_and_save(test_config, df)
    assert "<=50K" in result["classification_report"]
    assert ">50K" in result["classification_report"]
