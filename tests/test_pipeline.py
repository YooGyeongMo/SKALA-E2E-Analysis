"""엔드투엔드 스모크 테스트: run_pipeline이 보고서와 산출물을 만든다."""

from pathlib import Path

from e2e.config import AppConfig
from e2e.pipeline import run_pipeline


def test_pipeline_end_to_end(test_config: AppConfig) -> None:
    """전 단계를 완주하고 report.md, 차트, joblib이 실제로 생성된다."""
    result = run_pipeline(test_config)

    report = Path(result["report_path"])
    assert report.exists() and report.stat().st_size > 0
    text = report.read_text(encoding="utf-8")
    assert "가설 검정" in text
    assert "Accuracy" in text

    assert Path(result["model"]["model_path"]).exists()
    for fig in result["figures"]:
        assert Path(fig).exists()


def test_pipeline_is_idempotent(test_config: AppConfig) -> None:
    """두 번 돌려도 오류 없이 같은 정제 결과가 나온다(schedule 전제)."""
    first = run_pipeline(test_config)
    second = run_pipeline(test_config)
    # 로딩 시간 측정값은 실행마다 달라지므로 멱등성 비교에서 제외한다
    first_clean = {k: v for k, v in first["clean"].items() if k != "loading"}
    second_clean = {k: v for k, v in second["clean"].items() if k != "loading"}
    assert first_clean == second_clean
    assert first["stats"]["p_value"] == second["stats"]["p_value"]
