# E2E Analysis Wiki

데이터 수집, 정제, 분석, 보고서 자동화 파이프라인의 설계 문서입니다.
`make run` 한 줄로 UCI Adult 데이터(32,561명)를 내려받아 정제하고, 통계 검정과 분류 모델을 돌린 뒤, 차트와 `output/report.md` 를 생성합니다.

## 페이지

| 페이지 | 내용 |
|---|---|
| [Architecture](Architecture.md) | 단계별 모듈, 데이터 흐름, 실행 방식(수동, 스케줄, CI) |
| [Tradeoffs](Tradeoffs.md) | 결정 로그: 상황, 선택지, 결정, 비용, 다시 볼 조건 |
| [Troubleshooting](Troubleshooting.md) | 실제로 겪은 문제, 원인, 해결, 전후 수치 |
| [Evaluation](Evaluation.md) | 가설 검정 절차와 모델 평가 3층 구조, 실측 결과 |
| [Schedule](Schedule.md) | 실제 타임라인, 이슈와 PR 로 일을 쪼갠 방식, 브랜치 전략 |

## 한눈에 보는 숫자

| 항목 | 값 | 출처 |
|---|---|---|
| 원본 > 정제 | 32,561행 > 30,139행 (중복 24, 결측 보유 2,399 제거) | `make run` 로그 |
| 평균 근로시간 차이 | 6.36시간, 95% CI [6.07, 6.64], d = 0.545 | `output/report.md` 3장 |
| 초과근무 비율 | 24.1% vs 49.8% (카이제곱 1760.4) | `output/report.md` 3장 |
| 분류 성능 | 내부 0.8457, 5-fold 0.8475 (±0.0069), 외부 0.8465 | `output/report.md` 4장 |
| 전체 실행 시간 | 3.0초 (캐시 사용 시) | `make run` 로그 |
| 테스트 | 38건, 커버리지 95.3% | `make test` |

## 관련 문서

- [README](../../README.md)
- [v1 보고서 아카이브](../reports/report-v1.md)
- [팀 회고 종합](../reports/team-retrospective.md)
- [팀원 개별 의견](../opinions/README.md)
