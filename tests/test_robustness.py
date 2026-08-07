"""예외처리와 폴백 검증: 분위수, 다운로드 재시도, 스케줄 잡 오류 격리."""

import importlib.util
import urllib.request
from pathlib import Path

import pytest

from e2e import extract as extract_mod
from e2e.clean import load_and_clean
from e2e.config import AppConfig
from e2e.stats import analyze

ROOT = Path(__file__).resolve().parents[1]


def test_group_stats_include_quartiles(test_config: AppConfig) -> None:
    """기술통계에 분위수(Q1/Q3)가 포함되고 순서가 올바르다."""
    df, _ = load_and_clean(test_config)
    result = analyze(test_config, df)
    for g in result["group_stats"]:
        assert g["q1"] <= g["median"] <= g["q3"]
        assert {"count", "mean", "q1", "median", "q3", "std"} <= set(g)


def test_download_retries_then_succeeds(
    test_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """일시적 네트워크 장애(2회 실패)에도 재시도로 복구한다."""
    target = tmp_path / "adult.csv"
    calls = {"n": 0}

    def flaky(url: str, path: str) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("일시적 네트워크 장애")
        Path(path).write_text("ok", encoding="utf-8")

    monkeypatch.setattr(urllib.request, "urlretrieve", flaky)
    monkeypatch.setattr(extract_mod.time, "sleep", lambda s: None)
    test_config.data.raw_path = target
    result = extract_mod.extract(test_config)
    assert result == target and target.exists()
    assert calls["n"] == 3


def test_download_final_failure_is_clear(
    test_config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """전부 실패하면 불완전 파일 없이 원인이 담긴 예외를 올린다."""

    def always_fail(url: str, path: str) -> None:
        Path(path).write_text("부분 다운로드", encoding="utf-8")  # 불완전 파일 흉내
        raise OSError("연결 거부")

    monkeypatch.setattr(urllib.request, "urlretrieve", always_fail)
    monkeypatch.setattr(extract_mod.time, "sleep", lambda s: None)
    target = tmp_path / "adult.csv"
    test_config.data.raw_path = target
    with pytest.raises(RuntimeError, match="3회 모두 실패"):
        extract_mod.extract(test_config)
    assert not target.exists(), "실패 시 불완전 파일이 남으면 안 된다(깨진 캐시 방지)"


def _load_runner() -> object:
    spec = importlib.util.spec_from_file_location(
        "schedule_runner", ROOT / "scripts" / "schedule_runner.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schedule_job_isolates_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """잡 내부 예외가 밖으로 전파되지 않는다(스케줄 루프 보호)."""
    runner = _load_runner()

    def boom(config: object) -> None:
        raise RuntimeError("파이프라인 폭발")

    monkeypatch.setattr(runner, "run_pipeline", boom)
    monkeypatch.setattr(runner, "load_config", lambda p: object())
    assert runner.job("config.yaml") is False  # 예외 대신 False


def test_schedule_job_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """잡이 성공하면 True를 반환한다(--once 종료 코드의 근거)."""
    runner = _load_runner()
    monkeypatch.setattr(runner, "run_pipeline", lambda c: {"ok": True})
    monkeypatch.setattr(runner, "load_config", lambda p: object())
    assert runner.job("config.yaml") is True
