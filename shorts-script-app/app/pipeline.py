"""앱의 4단계 파이프라인.

1) collect      떡상 쇼츠 검색 → 자막 추출 → 후킹 분석 → 후킹 멘트 라이브러리 누적
2) templates    분석 결과를 묶어 대본 템플릿으로 구조화
3) research     제품에 대한 국내외 커뮤니티/SNS 반응 조사 및 종합
4) script       리서치 + 템플릿 + 후킹 라이브러리로 쇼츠 대본 작성
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from . import communities, db, llm, youtube
from .seed_templates import SEED_TEMPLATES

log = logging.getLogger(__name__)


def init() -> None:
    db.init()
    if not db.list_templates():
        for t in SEED_TEMPLATES:
            db.save_template(t, source="seed")


# ---- 1. 떡상 영상 수집 & 후킹 분석 --------------------------------------------------------

def analyze_video(video_id: str, transcript: str | None = None) -> dict:
    video = db.get_video(video_id)
    if not video:
        raise ValueError(f"영상 {video_id}가 DB에 없습니다. 먼저 검색으로 수집하세요")
    if transcript:
        db.set_transcript(video_id, transcript, "manual")
    elif not video.get("transcript"):
        t = youtube.fetch_transcript(video_id)
        if t:
            db.set_transcript(video_id, t, "youtube")
    video = db.get_video(video_id)

    analysis = llm.analyze_video(video).model_dump()
    db.save_analysis(video_id, analysis)

    new_hooks = 0
    for h in analysis["hook_lines"]:
        new_hooks += db.add_hook({**h, "video_id": video_id, "views": video["views"],
                                  "viral_score": video["viral_score"]})
    return {"video_id": video_id, "analysis": analysis, "new_hooks": new_hooks,
            "had_transcript": bool(video.get("transcript"))}


def collect(keyword: str, days: int = 14, region: str = "KR", language: str = "ko",
            min_views: int = 50_000, analyze_top: int = 5) -> dict:
    videos = youtube.search_viral_shorts(keyword, days=days, region=region, language=language,
                                         min_views=min_views)
    for v in videos:
        db.upsert_video(v)

    targets = [v for v in videos if not db.get_analysis(v["video_id"])][:analyze_top]
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(analyze_video, v["video_id"]): v for v in targets}
        for f, v in futures.items():
            try:
                results.append(f.result())
            except Exception as e:  # 한 영상 실패가 전체 수집을 막지 않게
                log.exception("분석 실패 %s", v["video_id"])
                errors.append({"video_id": v["video_id"], "error": str(e)})
    return {
        "keyword": keyword,
        "found": len(videos),
        "analyzed": len(results),
        "new_hooks": sum(r["new_hooks"] for r in results),
        "errors": errors,
        "videos": videos[:30],
    }


# ---- 2. 템플릿 구조화 ------------------------------------------------------------------

def rebuild_templates(max_templates: int = 5) -> list[dict]:
    analyses = db.list_analyses(limit=30)
    if len(analyses) < 3:
        raise ValueError("템플릿을 만들려면 분석된 영상이 최소 3개 필요합니다")
    result = llm.build_templates(analyses, db.list_templates(), max_templates)
    for t in result.templates:
        db.save_template(t.model_dump(), source=f"analysis:{len(analyses)}videos")
    return db.list_templates()


# ---- 3. 제품 반응 리서치 ----------------------------------------------------------------

def research(product: str) -> dict:
    with ThreadPoolExecutor(max_workers=2) as ex:
        api_future = ex.submit(communities.collect_all, product)
        web_future = ex.submit(llm.web_research, product)
        collected = api_future.result()
        try:
            web = web_future.result()
        except llm.LLMError as e:
            web = {"notes": f"(웹검색 실패: {e})", "urls": []}

    report = llm.synthesize_research(product, collected, web).model_dump()
    raw = {"api": collected, "web": web}
    rid = db.save_research(product, raw, report)
    return {"id": rid, "product": product, "report": report,
            "source_counts": _source_counts(collected, web)}


def _source_counts(collected: dict, web: dict) -> dict:
    counts = {k: len([x for x in v if "error" not in x]) for k, v in collected.items()}
    counts["web_urls"] = len(web.get("urls", []))
    return counts


# ---- 4. 대본 작성 ---------------------------------------------------------------------

def generate_script(product: str, research_id: int | None = None, notes: str = "",
                    length_sec: int = 45, template_id: int | None = None) -> dict:
    if research_id is None:
        research_id = research(product)["id"]
    r = db.get_research(research_id)
    if not r:
        raise ValueError(f"리서치 {research_id}를 찾을 수 없습니다")

    templates = db.list_templates()
    if template_id:
        templates = [t for t in templates if t["id"] == template_id] or templates
    hooks = db.list_hooks(limit=60)

    script = llm.write_script(product, r["report"], templates, hooks, notes, length_sec).model_dump()
    chosen = next((t for t in templates if t["name"] == script["template_name"]), None)
    sid = db.save_script(product, research_id, chosen["id"] if chosen else None, script)
    return {"id": sid, "product": product, "research_id": research_id, "script": script}
