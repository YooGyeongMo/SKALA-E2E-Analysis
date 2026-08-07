"""SKALA Day2 종합실습: Adult Census 소득 데이터 End2End 분석 파이프라인.

구조 원칙: 각 단계(extract > clean > stats > model > visualize > report)는
독립 모듈이며, config.yaml을 Pydantic으로 검증한 AppConfig 객체 하나만
주입받는다. 단계가 분리되어 있으므로 실패 지점이 곧 책임 모듈이고,
단계별로 pytest를 붙일 수 있다.
"""

__version__ = "0.1.0"
