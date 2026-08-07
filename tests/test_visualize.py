"""시각화 산출물 검증: 파일이 실제로 생성되고 비어 있지 않다."""

from pathlib import Path

from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.visualize import visualize


def test_all_charts_created(test_config: AppConfig) -> None:
    """PNG 3종과 Plotly HTML 1종이 전부 생성된다."""
    df, _ = load_and_clean(test_config)
    saved = visualize(test_config, df)
    assert len(saved) == 4
    suffixes = sorted(Path(p).suffix for p in saved)
    assert suffixes == [".html", ".png", ".png", ".png"]
    for p in saved:
        path = Path(p)
        assert path.exists()
        assert path.stat().st_size > 1000, f"{p} 파일이 비정상적으로 작다"


def test_html_is_selfcontained(test_config: AppConfig) -> None:
    """Plotly HTML이 plotly.js를 내장해 오프라인에서도 열린다."""
    df, _ = load_and_clean(test_config)
    saved = visualize(test_config, df)
    html = next(p for p in saved if p.endswith(".html"))
    text = Path(html).read_text(encoding="utf-8")
    assert "plotly" in text.lower()
    assert len(text) > 100_000, "plotly.js가 내장되지 않은 것으로 보인다"
