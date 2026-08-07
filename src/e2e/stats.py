"""A 단계: 기술통계, 상관, 가설 검정(교차검증 포함).

주 가설 (config의 hypothesis_feature, target으로 선언)
- H0: 소득 그룹(<=50K vs >50K) 간 주당 근로시간 평균은 같다
- H1: 두 그룹의 평균은 다르다

검정 절차 설계 (분석 순서 그대로 코드화)
1) Levene 등분산 검정: 실측 p=0.0046으로 등분산 기각 > Student t 대신
   Welch t(equal_var=False)를 쓰는 근거를 코드로 남긴다
2) Welch t-test: 본검정
3) Mann-Whitney U 교차검증: 근로시간 분포는 40시간에 봉우리가 있는
   비정규 분포라서, 정규성에 기대지 않는 비모수 검정으로 같은 결론이
   나오는지 확인한다(결론의 강건성)
4) Cohen's d: n이 3만을 넘으면 미미한 차이도 p가 작게 나오는 대표본
   함정이 있어, 유의성(p)과 실질 크기(d)를 분리해 해석한다
5) 보조가설(연령): 같은 구조로 age를 검정해 스토리를 보강한다

해석 주의(사전 실측): 평균은 39.35 vs 45.71시간으로 다르지만 중앙값은
두 그룹 모두 40시간이다. 즉 "고소득자가 더 오래 일한다"보다
"고소득 그룹은 초과근무자 비중이 높다"가 정확하다(차이는 꼬리에서 온다).
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

AUX_FEATURE = "age"  # 보조가설 변수: 소득 그룹 간 평균 연령


def _cohens_d(a: pd.Series, b: pd.Series) -> float:
    """합동 표준편차 대비 평균 차이(효과의 실질 크기)."""
    pooled_std = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    return float(abs(a.mean() - b.mean()) / pooled_std)


def _p_display(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.4f}"


def _welch_test(a: pd.Series, b: pd.Series, alpha: float) -> dict[str, Any]:
    """Welch t + Cohen's d를 한 변수에 대해 수행한다(주가설, 보조가설 공용)."""
    t_res = sps.ttest_ind(a, b, equal_var=False)
    p_value = float(t_res.pvalue)
    return {
        "t_statistic": round(float(t_res.statistic), 2),
        "p_value": p_value,
        "p_display": _p_display(p_value),
        "significant": bool(p_value < alpha),
        "cohens_d": round(_cohens_d(a, b), 3),
        "mean_diff": round(float(abs(a.mean() - b.mean())), 2),
    }


def analyze(config: AppConfig, df: pd.DataFrame) -> dict[str, Any]:
    """기술통계, 상관행렬, 검정 3종(Levene/Welch/Mann-Whitney)과
    보조가설을 수행해 딕셔너리로 반환한다."""
    target = config.analysis.target
    feature = config.analysis.hypothesis_feature
    alpha = config.analysis.alpha

    group_stats = (
        df.groupby(target)[feature].agg(["count", "mean", "median", "std"]).round(2).reset_index()
    )
    labels = sorted(df[target].unique())
    a = df.loc[df[target] == labels[0], feature]
    b = df.loc[df[target] == labels[1], feature]

    # 1) 등분산 확인: Welch 선택의 근거
    levene_stat, levene_p = sps.levene(a, b)
    # 2) 본검정 + 4) 효과크기
    main = _welch_test(a, b, alpha)
    # 3) 비모수 교차검증
    mw_stat, mw_p = sps.mannwhitneyu(a, b)
    # 5) 보조가설: 연령
    aux_a = df.loc[df[target] == labels[0], AUX_FEATURE]
    aux_b = df.loc[df[target] == labels[1], AUX_FEATURE]
    aux = _welch_test(aux_a, aux_b, alpha)
    aux["feature"] = AUX_FEATURE
    aux["means"] = [round(float(aux_a.mean()), 2), round(float(aux_b.mean()), 2)]

    # 분산이 0인 컬럼은 상관계수가 정의되지 않아(0/0 = NaN) 제외한다
    numeric = df.select_dtypes("number")
    numeric = numeric.loc[:, numeric.std() > 0]
    corr = numeric.corr().round(3)

    result = {
        "feature": feature,
        "target": target,
        "alpha": alpha,
        "group_stats": group_stats.to_dict("records"),
        **main,
        "levene_stat": round(float(levene_stat), 2),
        "levene_p": float(levene_p),
        "levene_p_display": _p_display(float(levene_p)),
        "equal_var_rejected": bool(levene_p < alpha),
        "mannwhitney_u": round(float(mw_stat), 0),
        "mannwhitney_p": float(mw_p),
        "mannwhitney_p_display": _p_display(float(mw_p)),
        "cross_consistent": bool((mw_p < alpha) == (main["p_value"] < alpha)),
        "aux": aux,
        "corr_columns": list(corr.columns),
        "corr_rows": corr.values.tolist(),
    }
    logger.info(
        "[A] Levene p %s(등분산 %s) > Welch t=%.2f p %s, MW p %s(교차 %s), "
        "d=%.3f > H0 %s / 보조(%s): p %s",
        result["levene_p_display"],
        "기각" if result["equal_var_rejected"] else "유지",
        result["t_statistic"],
        result["p_display"],
        result["mannwhitney_p_display"],
        "일치" if result["cross_consistent"] else "불일치",
        result["cohens_d"],
        "기각(차이 실재)" if result["significant"] else "기각 실패",
        AUX_FEATURE,
        aux["p_display"],
    )
    return result
