"""V 단계: 로딩과 정제(결측, 중복).

핵심 주의사항: 슬라이드 예시의 na_values=" ?"는 skipinitialspace=True가
공백을 먼저 제거하기 때문에 결측 매칭에 실패한다(결측 0건으로 오인).
config의 na_token="?"를 사용해야 실제 결측이 잡힌다.
실측 검증: 전체 32,561행 중 결측 4,262셀(workclass 1,836 / occupation
1,843 / native-country 583), 중복 24행.

TODO(로딩 담당): Pandas vs Polars 로딩 시간 비교 실측 추가(요구사항)
TODO(로딩 담당): 결측 처리 전략 검토(현재는 행 제거, 대안: 최빈값 대체)
"""

import logging

import pandas as pd

from e2e.config import AppConfig

logger = logging.getLogger(__name__)


def load_and_clean(config: AppConfig) -> tuple[pd.DataFrame, dict[str, int]]:
    """원천 CSV를 로딩하고 결측 행과 중복 행을 제거한다.

    반환: (정제된 DataFrame, 전후 검증용 메타 딕셔너리)
    메타를 함께 반환하는 이유: 보고서에 "몇 건을 왜 지웠는지"를
    숫자로 남겨야 정제가 검증 가능해진다.
    """
    df = pd.read_csv(
        config.data.raw_path,
        header=None,
        names=config.data.columns,
        na_values=config.data.na_token,
        skipinitialspace=True,
    )
    rows_raw = len(df)
    missing_cells = int(df.isna().sum().sum())
    missing_rows = int(df.isna().any(axis=1).sum())
    duplicate_rows = int(df.duplicated().sum())

    df = df.drop_duplicates().dropna().reset_index(drop=True)

    meta = {
        "rows_raw": rows_raw,
        "missing_cells": missing_cells,
        "missing_rows": missing_rows,
        "duplicate_rows": duplicate_rows,
        "rows_clean": len(df),
    }
    logger.info(
        "[V] 원본 %s행 > 중복 %s행, 결측 보유 %s행 제거 > 정제 후 %s행 (결측 셀 %s개)",
        f"{rows_raw:,}",
        duplicate_rows,
        f"{missing_rows:,}",
        f"{len(df):,}",
        f"{missing_cells:,}",
    )
    return df, meta
