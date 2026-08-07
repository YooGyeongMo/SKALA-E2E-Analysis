"""통계 심화 검증: 교차검정 일치, 상관행렬, 보조가설."""

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.stats import analyze


def test_cross_validation_consistent(test_config: AppConfig) -> None:
    """심어 둔 신호(35 vs 45시간)를 Welch와 Mann-Whitney가 같은 결론으로 잡는다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    assert result["significant"] is True
    assert result["mannwhitney_p"] < result["alpha"]
    assert result["cross_consistent"] is True


def test_levene_reported(test_config: AppConfig) -> None:
    """Levene 결과가 포함된다(Welch 선택 근거의 코드화)."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    assert "levene_p" in result
    assert isinstance(result["equal_var_rejected"], bool)


def test_correlation_matrix_shape(test_config: AppConfig) -> None:
    """상관행렬이 수치 컬럼 수와 일치하는 정방행렬이고 대각선이 1이다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    numeric = df.select_dtypes("number")
    expected = numeric.loc[:, numeric.std() > 0].shape[1]
    n = len(result["corr_columns"])
    assert n == expected  # 분산 0 컬럼(상관 정의 불가)은 제외된다
    assert len(result["corr_rows"]) == n
    for i in range(n):
        assert result["corr_rows"][i][i] == 1.0


def test_aux_hypothesis_present(test_config: AppConfig) -> None:
    """보조가설(연령) 결과가 주가설과 같은 구조로 포함된다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    assert result["aux"]["feature"] == "age"
    assert "p_display" in result["aux"]
    assert len(result["aux"]["means"]) == 2
