"""README 아키텍처 그림 생성 스크립트.

실행: pip install diagrams (graphviz 필요) 후
    python docs/diagrams/architecture.py
결과: docs/images/architecture.png
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.storage import Storage
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.vcs import Github
from diagrams.programming.flowchart import (
    Delay,
    Document,
    InputOutput,
    MultipleDocuments,
    StoredData,
)
from diagrams.programming.language import Bash, Python

FONT = "Apple SD Gothic Neo"
OUT = Path(__file__).resolve().parents[1] / "images" / "architecture"

graph_attr = {
    "fontname": FONT,
    "fontsize": "15",
    "pad": "0.4",
    "nodesep": "0.55",
    "ranksep": "0.9",
    "bgcolor": "white",
    "splines": "spline",
}
node_attr = {"fontname": FONT, "fontsize": "12"}
edge_attr = {"fontname": FONT, "fontsize": "11"}

with Diagram(
    "데이터 수집, 정제, 분석, 보고서 자동화",
    filename=str(OUT),
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    with Cluster("실행 트리거"):
        make = Bash("make run")
        cron = Delay("schedule_runner\n매일 08:00")
    config = Document("config.yaml\n(Pydantic 검증)")

    uci = InputOutput("UCI Adult\nadult.data / adult.test")

    with Cluster("1. 수집 (extract.py)"):
        extract = Python("다운로드\n재시도 3회")
        raw = Storage("data/raw 캐시\n(멱등)")

    with Cluster("2. 정제 (clean.py)"):
        clean = Python("Pandas vs Polars\n로딩 비교, 결측/중복 제거")

    with Cluster("3. 분석"):
        stats = Python("stats.py\nLevene, Welch t, MW U,\n카이제곱, 로지스틱 회귀")
        model = Python("model.py\nsklearn Pipeline\nCV 5-fold, 외부 검증")
        viz = Python("visualize.py\nSeaborn, Plotly")

    with Cluster("4. 보고서 (report.py)"):
        render = Python("Jinja2 렌더")
        report = Document("output/report.md")

    joblib = StoredData("model.joblib")
    figs = MultipleDocuments("PNG 6종\n+ Plotly HTML")

    with Cluster("품질 게이트"):
        gh = Github("PR")
        ci = GithubActions("CI 3 OS x Py 3.11/3.13\nruff, mypy, pytest 80%")

    make >> Edge(label="python -m e2e") >> extract
    cron >> Edge(label="--once / 매일", style="dashed") >> extract
    config >> Edge(label="설정 주입 (전 단계 공유)", style="dotted") >> extract
    uci >> Edge(label="HTTP (캐시 없을 때만)") >> extract >> Edge(label="CSV 저장") >> raw
    raw >> Edge(label="CSV 로딩") >> clean
    clean >> Edge(label="DataFrame") >> stats
    clean >> Edge(label="DataFrame") >> model
    clean >> Edge(label="DataFrame") >> viz
    model >> Edge(label="joblib 저장, 재로딩 검증") >> joblib
    viz >> Edge(label="파일 저장") >> figs
    stats >> Edge(label="결과 dict") >> render
    model >> Edge(label="결과 dict") >> render
    viz >> Edge(label="경로 list") >> render
    render >> Edge(label="렌더링") >> report
    gh >> Edge(label="pull_request") >> ci
