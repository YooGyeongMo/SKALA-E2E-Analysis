"""V 단계: 로딩(Pandas vs Polars 비교)과 정제(결측, 중복).

결측 토큰 함정: 슬라이드 예시의 na_values=" ?"는 skipinitialspace=True가
공백을 먼저 제거하기 때문에 결측 매칭에 실패한다(결측 0건으로 오인).
config의 na_token="?"를 사용해야 실제 결측이 잡힌다. 두 방식을 나란히
실행해 검증했으며, 구체적인 결측/중복 수치는 자동 생성 보고서가 담당한다
(주석에 실행 결과값을 적으면 조건 변경 시 코드와 결과가 어긋난다).

Pandas vs Polars 비교 설계
- 측정 범위는 "파일에서 분석 가능한 상태까지"로 통일한다. 원본은 값 앞에
  공백이 있는데 Pandas는 skipinitialspace 옵션이 내장이지만 Polars는
  로딩 후 strip_chars를 직접 해야 하므로, 그 후처리까지 시간에 포함해야
  공정한 비교다(순수 파싱만 재면 Polars에 유리하게 왜곡됨)
- 동일성 검증 포함: 행수와 결측 셀 수가 두 도구에서 일치해야 비교가
  의미를 갖는다(속도만 재고 결과가 다르면 무의미)
- 이후 단계는 Pandas DataFrame을 사용한다: sklearn, seaborn, scipy가
  모두 Pandas를 표준 입력으로 받으므로 변환 비용 없이 흐른다

결측 처리 전략: 행 제거(dropna)를 선택했다
- 결측 비율이 한 자릿수 퍼센트라 제거해도 충분한 표본이 남는다
- 결측이 일부 범주 컬럼에 몰려 있어 최빈값 대체 시 특정 범주가
  인위적으로 부풀어 분포를 왜곡한다
- 예측 서비스가 아니라 그룹 비교 분석이 목적이므로 보수적 제거가 안전
"""

import logging
import time
from typing import Any

import pandas as pd
import polars as pl

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

# 로딩 시간 측정 반복 횟수: 최솟값을 취해 OS 캐시나 순간 부하의 영향을 줄인다
TIMING_RUNS = 3


def _load_pandas(config: AppConfig) -> pd.DataFrame:
    """Pandas 로딩: skipinitialspace가 값 앞 공백을 제거한다."""
    return pd.read_csv(
        config.data.raw_path,
        header=None,
        names=config.data.columns,
        na_values=config.data.na_token,
        skipinitialspace=True,
    )


def _load_polars(config: AppConfig) -> pl.DataFrame:
    """Polars 로딩: 공백 제거와 결측 치환을 후처리로 수행한다.

    infer_schema=False로 전부 문자열로 읽는 이유: 값 앞 공백(" 39") 탓에
    수치 추론이 실패할 수 있어, strip 후에 수치 컬럼만 명시적으로 캐스팅.
    """
    df = pl.read_csv(
        config.data.raw_path,
        has_header=False,
        new_columns=config.data.columns,
        infer_schema=False,
    )
    df = df.with_columns(pl.all().str.strip_chars())
    df = df.with_columns(
        pl.when(pl.all() == config.data.na_token).then(None).otherwise(pl.all()).name.keep()
    )
    # 파일 끝 빈 줄 처리: Pandas는 skip_blank_lines=True가 기본이라 건너뛰지만
    # Polars는 전부 null인 행 1개로 파싱한다(실측: 원본이 \n\n으로 끝나
    # 32,562행 + 결측 15셀로 불일치). Pandas 기본 동작에 정렬한다.
    df = df.filter(~pl.all_horizontal(pl.all().is_null()))
    numeric_cols = [
        "age",
        "fnlwgt",
        "education-num",
        "capital-gain",
        "capital-loss",
        "hours-per-week",
    ]
    return df.with_columns([pl.col(c).cast(pl.Int64) for c in numeric_cols])


def compare_loading(config: AppConfig) -> dict[str, Any]:
    """두 도구의 로딩 시간을 재고 결과 동일성(행수, 결측)을 검증한다."""
    pandas_times, polars_times = [], []
    pdf = _load_pandas(config)
    plf = _load_polars(config)
    for _ in range(TIMING_RUNS):
        start = time.perf_counter()
        pdf = _load_pandas(config)
        pandas_times.append(time.perf_counter() - start)
        start = time.perf_counter()
        plf = _load_polars(config)
        polars_times.append(time.perf_counter() - start)

    pandas_sec = min(pandas_times)
    polars_sec = min(polars_times)
    result = {
        "pandas_sec": round(pandas_sec, 4),
        "polars_sec": round(polars_sec, 4),
        "speedup": round(pandas_sec / polars_sec, 2),
        "rows_match": len(pdf) == len(plf),
        "nulls_match": int(pdf.isna().sum().sum()) == int(plf.null_count().sum_horizontal()[0]),
        "timing_runs": TIMING_RUNS,
    }
    # 불일치는 속도 비교의 전제가 깨진 것이므로 경고 레벨로 크게 남긴다
    log = logger.info if (result["rows_match"] and result["nulls_match"]) else logger.warning
    log(
        "[V] 로딩 비교(각 %d회 최솟값): Pandas %.4fs vs Polars %.4fs (%.2f배), "
        "행수 일치=%s, 결측 일치=%s",
        TIMING_RUNS,
        pandas_sec,
        polars_sec,
        result["speedup"],
        result["rows_match"],
        result["nulls_match"],
    )
    return result


def load_and_clean(config: AppConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    """원천 CSV를 로딩하고 결측 행과 중복 행을 제거한다.

    반환: (정제된 DataFrame, 전후 검증용 메타 딕셔너리)
    메타를 함께 반환하는 이유: 보고서에 "몇 건을 왜 지웠는지"를
    숫자로 남겨야 정제가 검증 가능해진다.
    """
    loading = compare_loading(config)
    df = _load_pandas(config)
    rows_raw = len(df)
    missing_cells = int(df.isna().sum().sum())
    missing_rows = int(df.isna().any(axis=1).sum())
    duplicate_rows = int(df.duplicated().sum())

    # 정제 전 기준값: 결측이 특정 컬럼에 몰려 있으므로, 행 제거가 표본의
    # 대표성(타깃 비율, 가설 변수 분포)을 왜곡하지 않았는지 전후로 비교한다.
    # 왜곡됐다면 이후 모든 검정과 모델이 편향된 표본 위에 서게 된다
    target = config.analysis.target
    feature = config.analysis.hypothesis_feature
    positive = config.analysis.positive_label
    before = {
        "positive_ratio": float((df[target] == positive).mean()) * 100,
        "feature_mean": float(df[feature].mean()),
        "feature_median": float(df[feature].median()),
    }

    df = df.drop_duplicates().dropna().reset_index(drop=True)

    preservation = {
        "positive_ratio_before": round(before["positive_ratio"], 2),
        "positive_ratio_after": round(float((df[target] == positive).mean()) * 100, 2),
        "feature_mean_before": round(before["feature_mean"], 2),
        "feature_mean_after": round(float(df[feature].mean()), 2),
        "feature_median_before": round(before["feature_median"], 1),
        "feature_median_after": round(float(df[feature].median()), 1),
    }
    preservation["ratio_shift_pp"] = round(
        abs(preservation["positive_ratio_after"] - preservation["positive_ratio_before"]), 2
    )

    meta: dict[str, Any] = {
        "rows_raw": rows_raw,
        "missing_cells": missing_cells,
        "missing_rows": missing_rows,
        "duplicate_rows": duplicate_rows,
        "rows_clean": len(df),
        "loading": loading,
        "preservation": preservation,
    }
    logger.info(
        "[V] 원본 %s행 > 중복 %s행, 결측 보유 %s행 제거 > 정제 후 %s행 (결측 셀 %s개)",
        f"{rows_raw:,}",
        duplicate_rows,
        f"{missing_rows:,}",
        f"{len(df):,}",
        f"{missing_cells:,}",
    )
    logger.info(
        "[V] 분포 보존: 고소득 비율 %.2f%% > %.2f%% (변화 %.2f%%p), %s 평균 %.2f > %.2f",
        preservation["positive_ratio_before"],
        preservation["positive_ratio_after"],
        preservation["ratio_shift_pp"],
        feature,
        preservation["feature_mean_before"],
        preservation["feature_mean_after"],
    )
    return df, meta
