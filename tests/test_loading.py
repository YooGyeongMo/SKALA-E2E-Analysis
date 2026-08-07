"""Pandas vs Polars 로딩 비교의 동일성과 측정값 검증."""

from e2e.clean import compare_loading, load_and_clean
from e2e.config import AppConfig


def test_both_tools_read_identical_data(test_config: AppConfig) -> None:
    """행수와 결측 셀 수가 두 도구에서 일치한다(속도 비교의 전제)."""
    result = compare_loading(test_config)
    assert result["rows_match"] is True
    assert result["nulls_match"] is True


def test_timing_values_are_positive(test_config: AppConfig) -> None:
    """측정 시간이 양수이고 speedup이 계산된다."""
    result = compare_loading(test_config)
    assert result["pandas_sec"] > 0
    assert result["polars_sec"] > 0
    assert result["speedup"] > 0


def test_meta_includes_loading_comparison(test_config: AppConfig) -> None:
    """load_and_clean 메타에 로딩 비교가 포함되어 보고서로 흐른다."""
    _, meta = load_and_clean(test_config)
    assert "loading" in meta
    assert meta["loading"]["rows_match"] is True
