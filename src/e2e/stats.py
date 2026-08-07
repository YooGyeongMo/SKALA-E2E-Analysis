"""A 단계: 기술통계, 상관, 가설 검정.

주 가설 (config의 hypothesis_feature, target으로 선언)
- H0: 두 소득 그룹의 주당 근로시간 평균은 같다
- H1: 두 그룹의 평균은 다르다

검정 절차 설계 (분석 순서 그대로 코드화)
1) Levene 등분산 검정: 등분산이 기각되면 Student t 대신 Welch t를 쓴다.
   선택의 근거를 코드로 남기기 위해 결과를 함께 보고한다
2) Welch t-test: 본검정 (평균 차이). 평균 차이의 신뢰구간을 병기해
   효과의 크기와 불확실성을 함께 전달한다
3) Mann-Whitney U: 역할 구분에 주의. 이 검정의 대상은 평균이 아니라
   순위(분포의 위치)이므로 같은 가설의 반복이 아니다. 근로시간처럼
   표준 근무제 봉우리가 있는 비정규 분포에서, 정규성에 기대지 않는
   방법으로도 같은 방향의 결론이 나오는지 강건성을 확인하는 용도다
4) Cohen's d: 대표본에서는 미미한 차이도 p가 작아지므로, 유의성(p)과
   실질 크기(d)를 분리해 해석한다
5) 초과근무 비율 검정: 중앙값이 두 그룹에서 같게 나오면 "평균이 다르다"는
   결론만으로는 부족하다. 해석("초과근무자 비중이 높다")을 비중 그 자체로
   검정해야 논증이 닫힌다 (이진화 후 카이제곱 독립성 검정)
6) 보조가설(연령): 같은 구조로 한 번 더. 단, 탐색적 보강 목적이며
   다중비교 보정을 하지 않았으므로 주가설과 동등한 근거로 쓰지 않는다
   (이 한계는 보고서에 명시한다)

구체적인 실측 수치는 자동 생성 보고서(output/report.md)가 담당한다.
주석에 실행 결과값을 적으면 분석 조건이 바뀔 때 코드와 결과가 어긋난다.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps

from e2e.config import AppConfig

logger = logging.getLogger(__name__)

AUX_FEATURE = "age"  # 보조가설 변수: 소득 그룹 간 평균 연령
OVERTIME_THRESHOLD = 40  # 초과근무 기준(주 40시간 표준 근무제)
CONFIDENCE = 0.95  # 평균 차이 신뢰구간 수준


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


def _welch_ci(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    """평균 차이(b - a)의 Welch 신뢰구간.

    p는 "차이가 0인가"만 답하지만, 신뢰구간은 "차이가 어느 범위에
    있는가"까지 답한다. Welch-Satterthwaite 자유도로 등분산을 가정하지
    않는다.
    """
    diff = float(b.mean() - a.mean())
    va, vb = a.var() / len(a), b.var() / len(b)
    se = float(np.sqrt(va + vb))
    dof = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    t_crit = float(sps.t.ppf((1 + CONFIDENCE) / 2, dof))
    return round(diff - t_crit * se, 2), round(diff + t_crit * se, 2)


def _overtime_test(
    df: pd.DataFrame, target: str, feature: str, labels: list[str], alpha: float
) -> dict[str, Any]:
    """핵심 해석("초과근무자 비중이 높다")을 비중 그 자체로 검정한다.

    기준 초과 여부로 이진화한 뒤 소득 그룹 x 초과 여부 교차표에
    카이제곱 독립성 검정을 적용한다. 평균 검정과 별개의 질문
    ("비중이 다른가")에 답하는 검정이다.
    """
    over = df[feature] > OVERTIME_THRESHOLD
    table = pd.crosstab(df[target], over)
    chi2, p, _, _ = sps.chi2_contingency(table)
    rates = {label: round(float(over[df[target] == label].mean()) * 100, 1) for label in labels}
    return {
        "threshold": OVERTIME_THRESHOLD,
        "rates": rates,
        "chi2": round(float(chi2), 1),
        "p_value": float(p),
        "p_display": _p_display(float(p)),
        "significant": bool(p < alpha),
    }


def analyze(config: AppConfig, df: pd.DataFrame) -> dict[str, Any]:
    """기술통계, 상관행렬, 검정(Levene/Welch/CI/Mann-Whitney/비율)과
    보조가설을 수행해 딕셔너리로 반환한다."""
    target = config.analysis.target
    feature = config.analysis.hypothesis_feature
    alpha = config.analysis.alpha

    group_stats = (
        df.groupby(target)[feature].agg(["count", "mean", "median", "std"]).round(2).reset_index()
    )
    labels = sorted(df[target].unique())
    # 이 분석 전체가 2그룹 비교를 전제한다. 정제 로직 변경으로 그룹이
    # 늘면 아래 로직이 세 번째 그룹을 조용히 무시하므로 즉시 실패시킨다
    assert len(labels) == 2, f"타깃 그룹이 2개여야 한다: {labels}"
    a = df.loc[df[target] == labels[0], feature]
    b = df.loc[df[target] == labels[1], feature]

    # 1) 등분산 확인: Welch 선택의 근거
    levene_stat, levene_p = sps.levene(a, b)
    # 2) 본검정 + 신뢰구간 + 4) 효과크기
    main = _welch_test(a, b, alpha)
    ci_low, ci_high = _welch_ci(a, b)
    # 3) 비모수 강건성 확인: 유의성뿐 아니라 방향까지 일치해야 한다.
    #    U가 기대값(n1*n2/2)보다 크면 첫 그룹의 순위가 높다는 뜻이므로
    #    평균 차이의 부호와 방향이 같은지 함께 검사한다
    mw_stat, mw_p = sps.mannwhitneyu(a, b)
    mw_a_higher = float(mw_stat) > (len(a) * len(b)) / 2
    mean_a_higher = bool(a.mean() > b.mean())
    direction_consistent = mw_a_higher == mean_a_higher
    # 5) 핵심 해석의 직접 검정: 초과근무 비율
    overtime = _overtime_test(df, target, feature, labels, alpha)
    # 6) 보조가설: 연령 (탐색적 보강, 다중비교 보정 없음)
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
        "ci_low": ci_low,
        "ci_high": ci_high,
        "confidence": CONFIDENCE,
        "mannwhitney_u": round(float(mw_stat), 0),
        "mannwhitney_p": float(mw_p),
        "mannwhitney_p_display": _p_display(float(mw_p)),
        "cross_consistent": bool(
            ((mw_p < alpha) == (main["p_value"] < alpha)) and direction_consistent
        ),
        "overtime": overtime,
        "aux": aux,
        "corr_columns": list(corr.columns),
        "corr_rows": corr.values.tolist(),
    }
    logger.info(
        "[A] Levene p %s(등분산 %s) > Welch t=%.2f p %s, CI[%.2f, %.2f], "
        "MW p %s(방향 포함 교차 %s), d=%.3f > H0 %s",
        result["levene_p_display"],
        "기각" if result["equal_var_rejected"] else "유지",
        result["t_statistic"],
        result["p_display"],
        ci_low,
        ci_high,
        result["mannwhitney_p_display"],
        "일치" if result["cross_consistent"] else "불일치",
        result["cohens_d"],
        "기각(차이 실재)" if result["significant"] else "기각 실패",
    )
    logger.info(
        "[A] 초과근무(>%d시간) 비율 %s%% vs %s%% (chi2=%.1f, p %s) / 보조(%s) p %s",
        overtime["threshold"],
        overtime["rates"][labels[0]],
        overtime["rates"][labels[1]],
        overtime["chi2"],
        overtime["p_display"],
        AUX_FEATURE,
        aux["p_display"],
    )
    return result
