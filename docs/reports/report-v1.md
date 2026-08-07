# 분석 v1 아카이브 (2026-08-07 17:08 실행 기준)

v2 분석 개선(#15) 전의 상태를 원본 그대로 보존한다.
아래 실행 로그와 보고서는 실제 실행 출력을 가공 없이 옮긴 것이며,
맨 아래에 수치 크로스체크 결과와 v2에서 달라질 항목을 기록한다.

- 실행 환경: macOS, Python 3.11.15, 커밋 61c1609
- 실행 방식: make clean 후 make setup, make run, make test (콜드 스타트 전체 재현)

## 1. make run 실행 캡처 (원본 로그)

```text
$ make run
.venv/bin/python -m e2e
17:08:48 INFO e2e.pipeline === 파이프라인 시작: adult-income-analysis ===
17:08:48 INFO e2e.extract [E] 다운로드 시작: https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data
17:08:51 INFO e2e.extract [E] 저장 완료: data/raw/adult.csv (3,974,305 bytes)
17:08:51 INFO e2e.clean [V] 로딩 비교(각 3회 최솟값): Pandas 0.0165s vs Polars 0.0068s (2.42배), 행수 일치=True, 결측 일치=True
17:08:51 INFO e2e.clean [V] 원본 32,561행 > 중복 24행, 결측 보유 2,399행 제거 > 정제 후 30,139행 (결측 셀 4,262개)
17:08:51 INFO e2e.stats [A] Levene p < 0.001(등분산 기각) > Welch t=-43.17 p < 0.001, MW p < 0.001(교차 일치), d=0.545 > H0 기각(차이 실재) / 보조(age): p < 0.001
17:08:52 INFO e2e.model [M] LogisticRegression: accuracy=0.8457, F1=0.6601
17:08:52 INFO e2e.model [M] RandomForest: accuracy=0.8465, F1=0.6746
17:08:52 INFO e2e.model [M] 저장 모델=LogisticRegression (train 24,111 / test 6,028), 재로딩 일치=True
17:08:53 INFO e2e.visualize [Z] 차트 4개 저장: output/figures/boxplot_hours_by_income.png, output/figures/hist_hours_density.png, output/figures/heatmap_correlation.png, output/figures/education_income_rate.html
17:08:53 INFO e2e.report [R] 보고서 생성: output/report.md (6,260 bytes)
17:08:53 INFO e2e.pipeline === 파이프라인 완료: 4.7초, 보고서 output/report.md ===
```

## 2. make test 실행 캡처 (요약)

```text
$ make test
collected 21 items
tests/test_config.py ...        tests/test_loading.py ...
tests/test_model_compare.py ... tests/test_pipeline.py ..
tests/test_stages.py ....       tests/test_stats_deep.py ....
tests/test_visualize.py ..

Name                   Stmts   Miss  Cover
src/e2e/clean.py          45      0   100%
src/e2e/config.py         35      0   100%
src/e2e/model.py          48      0   100%
src/e2e/pipeline.py       23      0   100%
src/e2e/report.py         18      0   100%
src/e2e/stats.py          39      0   100%
src/e2e/visualize.py      77      1    99%
TOTAL                    320     25    92%
Required test coverage of 80% reached. Total coverage: 92.19%
21 passed, 10 warnings in 4.28s
```

참고: 10 warnings는 오류가 아니라 seaborn 라이브러리 내부가 matplotlib의
구버전 옵션(vert)을 쓰고 있다는 예고이며 우리 코드가 수정할 대상이 아니다.

## 3. v1 보고서 원문 (output/report.md 로우값 그대로)

````markdown
# adult-income-analysis 분석 보고서

자동 생성: 2026-08-07 17:08:53 (이 문서는 파이프라인이 렌더링한다. 직접 수정 금지)

## 요약 (한 문단)

1994년 미국 인구조사 기반 Adult 데이터 32,561명을 정제해
30,139명을 분석했다. 소득 그룹 간 주당 근로시간은
평균 6.36시간 차이가 있었고(Welch t, p < 0.001),
효과크기는 중간 수준(Cohen's d = 0.545)이다. 다만 중앙값은 두 그룹
모두 40시간으로 같아, 정확한 해석은 "고소득 그룹은 초과근무자 비중이 높다"이다.
이 신호를 학습한 분류 모델은 accuracy 0.8457, F1 0.6601을 기록했다.

## 1. 데이터 준비

### 1.1 로딩: Pandas vs Polars (3회 측정, 최솟값 비교)

| 도구 | 로딩 시간 | 비고 |
|---|---|---|
| Pandas | 0.0165초 | skipinitialspace로 공백 처리 내장 |
| Polars | 0.0068초 | strip과 결측 치환 후처리 포함 |

- Polars가 2.42배 빠름 (측정 범위: 파일에서 분석 가능한 상태까지)
- 동일성 검증: 행수 일치 = True, 결측 셀 수 일치 = True
- 이후 단계는 Pandas를 사용: sklearn, seaborn, scipy가 Pandas를 표준 입력으로 받는다

### 1.2 정제

| 항목 | 값 |
|---|---|
| 원본 행수 | 32,561 |
| 중복 행 제거 | 24 |
| 결측 보유 행 제거 | 2,399 (결측 셀 4,262개) |
| 정제 후 행수 | 30,139 |

주의: 결측 토큰은 "?"로 지정해야 탐지된다. 제공된 예시처럼 " ?"로 지정하면
skipinitialspace가 공백을 먼저 제거해 결측 0건으로 오인하게 된다(직접 실측으로 확인).
결측 행 제거를 택한 근거: 전체의 7.4%로 제거 후에도 표본 3만 이상, 결측이 범주
컬럼(workclass/occupation/native-country)에 몰려 있어 최빈값 대체 시 분포 왜곡 위험.

## 2. 시각화

![소득 그룹별 주당 근로시간 분포](figures/boxplot_hours_by_income.png)

![소득 그룹별 주당 근로시간 밀도 분포](figures/hist_hours_density.png)

두 그룹 모두 주 40시간에 봉우리가 있고(표준 근무제의 흔적), 고소득 그룹은
40시간 오른쪽 꼬리(초과근무)가 두껍다. 평균 차이는 이 꼬리에서 온다.

![수치 변수 간 상관계수](figures/heatmap_correlation.png)

인터랙티브: [교육수준별 고소득 비율 (Plotly HTML)](figures/education_income_rate.html)

## 3. 가설 검정: 소득 그룹 간 hours-per-week

- H0: 두 소득 그룹의 hours-per-week 평균은 같다
- H1: 두 그룹의 평균은 다르다 (유의수준 0.05)

| income | n | 평균 | 중앙값 | 표준편차 |
|---|---|---|---|---|
| <=50K | 22,633 | 39.35 | 40.0 | 11.95 |
| >50K | 7,506 | 45.71 | 40.0 | 10.74 |

### 검정 절차 (분석 순서 그대로)

| 단계 | 결과 | 판단 |
|---|---|---|
| 1. Levene 등분산 | stat = 20.63, p < 0.001 | 등분산 기각 > Welch 사용 |
| 2. Welch t (본검정) | t = -43.17, p < 0.001 | H0 기각 |
| 3. Mann-Whitney U (교차) | U = 56,299,256, p < 0.001 | 비모수에서도 결론 일치 |
| 4. Cohen's d (효과크기) | d = 0.545 | 중간 효과 |

- 판정: 평균 차이 6.36시간은 우연으로 설명되지 않는다 (p < 0.001)
- Mann-Whitney를 병행한 이유: 근로시간 분포는 40시간 봉우리가 있는 비정규
  분포라서, 정규성에 기대지 않는 검정으로도 같은 결론인지 확인했다
- 해석 주의 1 (대표본 함정): 표본이 3만이면 미미한 차이도 p가 작아진다.
  p는 "차이가 실재하는가", d는 "차이가 큰가"라는 별개의 질문에 답한다
- 해석 주의 2 (중앙값): 두 그룹 모두 중앙값 40시간. "고소득자가 더 오래
  일한다"가 아니라 "고소득 그룹은 초과근무자 비중이 높다"가 정확하다

### 보조가설: 소득 그룹 간 평균 연령

- 그룹 평균 36.61세 vs 43.96세,
  Welch t = -49.48, p < 0.001,
  d = 0.577 > 고소득 그룹이 평균적으로 나이가 많다
  (경력 축적과 소득의 관계로 해석 가능, 인과 주장은 아님)

## 4. 머신러닝

### 4.1 모델 비교 (동일 분할, 동일 전처리)

| 모델 | Accuracy | F1 (양성 = >50K) |
|---|---|---|
| LogisticRegression | 0.8457 | 0.6601 |
| RandomForest | 0.8465 | 0.6746 |

- 저장(배포) 모델은 LogisticRegression: 계수로 해석 가능한 기준선.
  과제 목적이 Pipeline 구성 검증이므로 성능 우위보다 해석 가능성을 우선했다
- 분할: 학습 24,111 / 평가 6,028 (stratify로 클래스 비율 유지)
- 저장: output/model.joblib (재로딩 예측 일치 = True)

### 4.2 상세 평가 (LogisticRegression)

```
              precision    recall  f1-score   support

       <=50K       0.88      0.93      0.90      4527
        >50K       0.73      0.60      0.66      1501

    accuracy                           0.85      6028
   macro avg       0.80      0.76      0.78      6028
weighted avg       0.84      0.85      0.84      6028

```

지표 선택 근거: 클래스 불균형(약 76:24)에서 accuracy만 보면 다수 클래스로만
찍어도 높게 나오므로 소수 클래스 성능을 반영하는 F1을 함께 본다.
MSE와 R2는 회귀 지표라 분류인 이 문제에 쓰지 않는다.

## 5. 결론과 한계

### 스토리라인
1. 시각화: 분포에서 차이가 보인다 (박스플롯, 밀도 히스토그램)
2. 검정: 그 차이는 통계적으로 실재하고(p < 0.001) 실질 크기도 중간(d = 0.545)
3. 모델: 그 신호로 소득을 예측할 수 있다 (accuracy 0.8457, F1 0.6601)

### 한계 (데이터로 반박할 수 없어 기록으로 남긴다)
- 자기응답 데이터: 측정된 것은 "응답한 근로시간"이지 실제 근로가 아니다
- 상관이지 인과가 아니다: "오래 일해서 고소득"인지 "고소득 직종이 장시간
  노동"인지 이 데이터로는 구분할 수 없다
- 인구 가중치(fnlwgt) 미적용: 모집단 추정이 아닌 표본 내 그룹 비교가 목적
- 1994년 자료: 현재 노동시장에 그대로 일반화할 수 없다

## 부록: 생성 산출물

- output/figures/boxplot_hours_by_income.png
- output/figures/hist_hours_density.png
- output/figures/heatmap_correlation.png
- output/figures/education_income_rate.html
- output/model.joblib
````

## 4. 수치 크로스체크 (로그 vs 보고서 vs 산술 검산)

| 검사 항목 | 검산 | 판정 |
|---|---|---|
| 그룹 합 = 정제 행수 | 22,633 + 7,506 = 30,139 | 일치 |
| 분할 합 = 정제 행수 | 24,111 + 6,028 = 30,139 | 일치 |
| 8:2 분할 비율 | 30,139 x 0.2 = 6,027.8 > 6,028 | 일치 |
| 상세 평가 support 합 | 4,527 + 1,501 = 6,028 | 일치 |
| 클래스 비율 | 22,633 / 30,139 = 75.1% (보고서 "약 76:24") | 일치 |
| 평균 차이 | 45.71 - 39.35 = 6.36 | 일치 |
| F1 상호 확인 | 요약 0.6601 = 상세 평가 >50K f1 0.66 | 일치 |
| accuracy 상호 확인 | 4.1표 0.8457 = 상세 평가 0.85 | 일치 |
| 로그와 보고서 | 정제/검정/모델 수치 전 항목 동일 | 일치 |
| 차트와 본문 주장 | 박스플롯 중앙선 둘 다 40, 밀도 차트 40 봉우리와 오른쪽 꼬리, 히트맵 최대 상관 0.15 | 일치 |

참고: Levene 통계량이 정제 전 원본에서는 8.02, 보고서(정제 후)에서는 20.63으로
다른데 이는 오류가 아니라 검정 대상 데이터가 다르기 때문이다(둘 다 등분산 기각으로
결론 동일). 파이프라인은 정제 후 데이터로 검정하는 것이 올바른 순서다.

## 5. v2(#15)에서 달라질 항목 (예고)

1. 비율 검정 추가: 핵심 해석 "고소득 그룹은 초과근무자 비중이 높다"를
   hours > 40 이진화 + 카이제곱으로 직접 검정 (v1은 평균만 검정)
2. 평균 차이의 95% 신뢰구간 병기 (v1은 p와 d만 보고)
3. 외부 검증: UCI adult.test 16,281행으로 최종 평가 (v1은 내부 8:2 분할만)
4. cross_val 5-fold로 성능의 평균과 표준편차 보고 (v1은 단일 분할)
5. 오즈비 표: 어떤 피처가 소득 확률을 밀어올리는지 해석 (v1은 성능 수치만)
