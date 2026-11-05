"""외부 API(Claude, YouTube, 커뮤니티)를 가짜로 바꿔 전체 흐름을 검증한다.  실행: python -m pytest tests"""
import json

import pytest
from fastapi.testclient import TestClient

from app import communities, config, llm, youtube
from app.schemas import ResearchReport, ShortsScript, TemplateSet, VideoAnalysis


def fake(model):
    """스키마를 만족하는 최소 예시 객체 생성."""
    def build(schema, defs):
        if "$ref" in schema:
            return build(defs[schema["$ref"].split("/")[-1]], defs)
        if "enum" in schema:
            return schema["enum"][0]
        t = schema.get("type")
        if t == "object":
            return {k: build(v, defs) for k, v in schema["properties"].items()}
        if t == "array":
            return [build(schema["items"], defs), build(schema["items"], defs)]
        return {"string": "예시", "integer": 40, "number": 1.5, "boolean": True}[t]
    s = llm.strict_schema(model)
    data = build(s, s.get("$defs", {}))
    return model.model_validate(data)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    videos = [{"video_id": f"v{i}", "title": f"영상{i}", "channel_id": "c", "channel_title": "채널",
               "description": "", "published_at": "2026-11-01T00:00:00Z", "duration_sec": 30,
               "views": 1_000_000 - i, "likes": 1, "comments": 1, "subscribers": 5000,
               "viral_score": 200.0 - i, "views_per_hour": 10.0, "keyword": "리뷰"} for i in range(4)]
    monkeypatch.setattr(youtube, "search_viral_shorts", lambda *a, **k: videos)
    monkeypatch.setattr(youtube, "fetch_transcript", lambda vid: "[0.0s] 이거 사지 마세요")
    monkeypatch.setattr(communities, "collect_all", lambda p: {"reddit": [{"title": "good"}]})

    counter = iter(range(1000))

    def analysis(video):
        a = fake(VideoAnalysis)
        for h in a.hook_lines:
            h.text = f"후킹 {next(counter)}"
        return a
    monkeypatch.setattr(llm, "analyze_video", analysis)
    monkeypatch.setattr(llm, "build_templates", lambda *a: fake(TemplateSet))
    monkeypatch.setattr(llm, "web_research", lambda p: {"notes": "메모", "urls": ["https://x"]})
    monkeypatch.setattr(llm, "synthesize_research", lambda *a: fake(ResearchReport))

    def script(product, report, templates, hooks, notes, length):
        assert templates and hooks
        s = fake(ShortsScript)
        s.template_name = templates[0]["name"]
        return s
    monkeypatch.setattr(llm, "write_script", script)

    from app.main import app
    with TestClient(app) as c:
        yield c


def test_full_flow(client):
    assert client.get("/").status_code == 200
    st = client.get("/api/status").json()
    assert st["counts"]["templates"] == 5  # 기본 템플릿

    r = client.post("/api/collect", json={"keyword": "리뷰", "analyze_top": 3}).json()
    assert r["found"] == 4 and r["analyzed"] == 3 and r["new_hooks"] == 6 and not r["errors"]

    # 같은 수집을 다시 해도 이미 분석된 영상은 건너뛰고 남은 1개만 분석
    r = client.post("/api/collect", json={"keyword": "리뷰", "analyze_top": 3}).json()
    assert r["analyzed"] == 1

    hooks = client.get("/api/hooks").json()
    assert len(hooks["hooks"]) == 8
    hid = hooks["hooks"][0]["id"]
    client.post(f"/api/hooks/{hid}/favorite")
    assert client.get("/api/hooks").json()["hooks"][0]["favorite"] == 1

    assert client.get("/api/videos/v0/analysis").status_code == 200
    tpls = client.post("/api/templates/rebuild").json()
    assert len(tpls) == 6

    res = client.post("/api/research", json={"product": "에어팟 프로3"}).json()
    assert res["report"]["product_summary"]
    sc = client.post("/api/scripts", json={"product": "에어팟 프로3", "research_id": res["id"]}).json()
    assert sc["script"]["beats"]
    # 리서치 없이 바로 대본 요청하면 리서치를 자동 수행
    sc2 = client.post("/api/scripts", json={"product": "갤럭시 버즈"}).json()
    assert sc2["research_id"] != res["id"]
    assert len(client.get("/api/scripts").json()) == 2


def test_errors_are_400(client, monkeypatch):
    def boom(*a, **k):
        raise youtube.YouTubeError("YOUTUBE_API_KEY가 설정되지 않았습니다")
    monkeypatch.setattr(youtube, "search_viral_shorts", boom)
    r = client.post("/api/collect", json={"keyword": "x"})
    assert r.status_code == 400 and "YOUTUBE" in r.json()["detail"]
    assert client.post("/api/templates/rebuild").status_code == 400  # 분석 0개


def test_strict_schema_requires_all_fields():
    s = llm.strict_schema(ShortsScript)
    assert s["additionalProperties"] is False
    assert set(s["required"]) == set(s["properties"])
    assert "title_options" in s["properties"]


def test_duration_parse():
    assert youtube._iso_duration_to_sec("PT59S") == 59
    assert youtube._iso_duration_to_sec("PT1M5S") == 65
    assert youtube._iso_duration_to_sec("P0D") == 0
