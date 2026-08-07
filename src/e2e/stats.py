"""A 단계: 기술통계와 가설 검정.

주 가설 (config의 hypothesis_feature, target으로 선언)
- H0: 소득 그룹(<=50K vs >50K) 간 주당 근로시간 평균은 같다
- H1: 두 그룹의 평균은 다르다

설계 근거
- Welch t-test(equal_var=False) 사용: 사전 실측에서 Levene 검정이
  등분산을 기각(p=0.0046)했으므로 분산 동일 가정을 하지 않는 쪽이 안전
- Cohen's d 병행: n이 3만을 넘으면 미미한 차이도 p가 작게 나오는
  대표본 함정이 있어, 유의성(p)과 실질 크기(d)를 분리해 해석한다
- 사전 실측: 38.84 vs 45.47시간, p < 0.001, d = 0.55(중간 효과),
  중앙값은 두 그룹 모두 40시간 > "고소득 그룹은 초과근무자 비중이
  높다"가 정확한 해석(평균 차이는 분포의 꼬리에서 온다)

TODO(통계 담당): 수치 컬럼 상관행렬 추가(요구사항)
TODO(통계 담당): Levene, Mann-Whitney 교차검증 코드화, 보조가설(age)
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps

from e2e.config import AppConfig

logger = logging.getLogger(__name__)


def analyze(config: AppConfig, df: pd.DataFrame) -> dict[str, Any]:
    """그룹별 기술통계와 Welch t-test, Cohen's d를 계산해 딕셔너리로 반환한다."""
    target = config.analysis.target
    feature = config.analysis.hypothesis_feature
    alpha = config.analysis.alpha

    group_stats = (
        df.groupby(target)[feature].agg(["count", "mean", "median", "std"]).round(2).reset_index()
    )
    labels = sorted(df[target].unique())
    a = df.loc[df[target] == labels[0], feature]
    b = df.loc[df[target] == labels[1], feature]

    t_res = sps.ttest_ind(a, b, equal_var=False)
    # Cohen's d: 합동 표준편차 대비 평균 차이(효과의 실질 크기)
    pooled_std = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    cohens_d = float(abs(a.mean() - b.mean()) / pooled_std)
    p_value = float(t_res.pvalue)

    result = {
        "feature": feature,
        "target": target,
        "group_stats": group_stats.to_dict("records"),
        "t_statistic": round(float(t_res.statistic), 2),
        "p_value": p_value,
        "p_display": "< 0.001" if p_value < 0.001 else f"{p_value:.4f}",
        "alpha": alpha,
        "significant": bool(p_value < alpha),
        "cohens_d": round(cohens_d, 3),
        "mean_diff": round(float(abs(a.mean() - b.mean())), 2),
    }
    logger.info(
        "[A] t=%.2f, p %s, Cohen's d=%.3f > H0 %s",
        result["t_statistic"],
        result["p_display"],
        result["cohens_d"],
        "기각(차이 실재)" if result["significant"] else "기각 실패",
    )
    return result
