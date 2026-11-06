# Troubleshooting

## 1. 결측이 0건으로 보였다

| 항목 | 내용 |
|---|---|
| 증상 | `na_values=" ?"` 로 읽으면 결측 0건 |
| 원인 | `skipinitialspace=True` 가 값 앞 공백을 먼저 지워 `" ?"` 가 영원히 매칭되지 않음 |
| 해결 | `config.yaml` 의 `na_token: "?"` |
| 전후 | 결측 셀 0 > 4,262 (workclass 1,836 / occupation 1,843 / native-country 583), 정제 후 32,537행 > 30,139행 |
| 확인 방법 | 두 토큰으로 같은 파일을 읽어 결측 수와 정제 후 행수를 비교 (2026-11-05 재확인) |

## 2. Pandas 와 Polars 의 행 수 불일치 ([#11](https://github.com/YooGyeongMo/SKALA-E2E-Analysis/issues/11), [PR #12](https://github.com/YooGyeongMo/SKALA-E2E-Analysis/pull/12))

| 항목 | 내용 |
|---|---|
| 증상 | 실데이터 `make run` 로그에 `행수 일치=False` (32,561 vs 32,562, 결측 15셀 차이). 합성 데이터 테스트는 통과 |
| 원인 | 원본이 빈 줄로 끝남. Pandas 는 `skip_blank_lines=True` 기본, Polars 는 전 컬럼 null 행으로 파싱 |
| 해결 | `df.filter(~pl.all_horizontal(pl.all().is_null()))` 로 Pandas 동작에 정렬 |
| 회귀 방지 | 테스트 픽스처에 파일 끝 빈 줄 재현 |
| 교훈 | 검증값을 로그에 출력해 둔 덕에 발견. 합성 테스트만으로는 실데이터 특성을 못 잡는다 |

## 3. Polars 수치 컬럼 스키마 추론

| 항목 | 내용 |
|---|---|
| 증상 | 값 앞 공백(`" 39"`) 때문에 수치 컬럼 추론이 실패할 수 있음 |
| 해결 | `infer_schema=False` 로 전부 문자열로 읽고, strip 후 수치 6개 컬럼만 명시적으로 `Int64` 캐스팅 |

## 4. 외부 검증 accuracy 0.0000 ([#16](https://github.com/YooGyeongMo/SKALA-E2E-Analysis/issues/16))

| 항목 | 내용 |
|---|---|
| 증상 | adult.test 를 그대로 평가하면 모든 예측이 오답 |
| 원인 | 첫 줄 주석행(`|1x3 Cross validator`), 라벨 끝 마침표(`">50K."`) |
| 해결 | `skiprows=1`, `str.rstrip(".")` |
| 전후 | accuracy 0.0000 (마침표를 일부러 남긴 반증 실험) > 0.8465 (15,055행) |

## 5. 멱등성 테스트 간헐 실패

| 항목 | 내용 |
|---|---|
| 증상 | 같은 입력으로 두 번 돌린 결과 비교가 가끔 실패 |
| 원인 | 결과 dict 에 로딩 시간 측정값이 포함되어 실행마다 다름 |
| 해결 | 멱등성 비교에서 시간 키를 빼고 정제 결과와 p-value 만 비교 |

## 6. 상관행렬 대각선 NaN

| 항목 | 내용 |
|---|---|
| 증상 | 테스트 데이터에서 히트맵 대각선이 NaN |
| 원인 | 분산 0 인 컬럼(합성 데이터의 capital-gain)은 상관계수가 0/0 |
| 해결 | 분산 0 컬럼을 상관 대상에서 제외 |

## 7. CI 환경 차이

| 문제 | 원인 | 해결 |
|---|---|---|
| 차트 저장 실패 가능 | headless 러너 | pyplot import 전에 `matplotlib.use("Agg")` |
| 한글 폰트 없음 | Actions 러너 기본 이미지 | AppleGothic, Malgun Gothic, NanumGothic 순 탐색, 없으면 경고 후 진행 |

## 8. 소득 그룹이 2개가 아닐 때 조용히 무시

| 항목 | 내용 |
|---|---|
| 증상 | 타깃 그룹이 3개 이상이면 세 번째 그룹이 검정에서 빠짐 (팀원 박서영 리뷰) |
| 해결 | 그룹 수 assert 로 즉시 실패. 3그룹 주입 테스트로 검증 |

## 9. 다운로드 실패 시 깨진 캐시

| 항목 | 내용 |
|---|---|
| 위험 | 다운로드 중 끊기면 불완전 파일이 남아 다음 실행이 정상 캐시로 오인 |
| 해결 | 실패한 시도의 파일 즉시 삭제, 3회 재시도(2초 대기), 최종 실패 시 URL 을 담은 예외 ([PR #29](https://github.com/YooGyeongMo/SKALA-E2E-Analysis/pull/29)) |
